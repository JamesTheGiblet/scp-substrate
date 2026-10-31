"""DB-native rule engine. Reads rules from sc.db, derives links, logs events."""
import json
from datetime import datetime, timezone
from substrate import Substrate


def _log_fire(s, rule_id, source, rel, target, extra=None):
    payload = {"source": source, "type": rel, "target": target}
    if extra:
        payload.update(extra)
    s.conn.execute("""
        INSERT INTO events (event_type, capsule_id, payload)
        VALUES ('rule.fired', ?, ?)
    """, (rule_id, json.dumps(payload)))


def _eval_pair(s, rule_id, condition, effect):
    """Condition shape: {source, target}. Effect: {relationship}."""
    source  = condition.get("source")
    target  = condition.get("target")
    rel     = effect.get("relationship")
    fired, warnings = [], []

    if not (source and target and rel):
        return [], [f"{rule_id}: incomplete condition/effect — skipped"]

    src_ok = s.conn.execute("SELECT 1 FROM capsules WHERE id=?", (source,)).fetchone()
    tgt_ok = s.conn.execute("SELECT 1 FROM capsules WHERE id=?", (target,)).fetchone()
    if not (src_ok and tgt_ok):
        missing = [x for x, ok in [(source, src_ok), (target, tgt_ok)] if not ok]
        return [], [f"{rule_id}: missing capsule(s) {missing} — skipped"]

    with s.conn:
        cur = s.conn.execute("""
            INSERT OR IGNORE INTO links (source, type, target, metadata)
            VALUES (?, ?, ?, ?)
        """, (source, rel, target, json.dumps({"derived_by": rule_id})))
        if cur.rowcount:
            _log_fire(s, rule_id, source, rel, target)
            fired.append((rule_id, source, rel, target))

    return fired, warnings


def _eval_trust_above(s, rule_id, condition, effect):
    """Condition: {type: trust_above, threshold}. Effect: {relationship, derive_from}."""
    threshold   = float(condition.get("threshold", 0.5))
    derive_from = effect.get("derive_from")
    rel         = effect.get("relationship")
    fired, warnings = [], []

    if not (rel and derive_from):
        return [], [f"{rule_id}: trust_above needs 'relationship' and 'derive_from'"]

    rows = s.conn.execute("""
        SELECT ts.capsule_id AS id,
               ts.score * exp(-json_extract(c.state_json, '$.k') *
                              (julianday('now') - julianday(ts.computed_at))) AS trust
        FROM trust_scores ts
        JOIN capsules c ON c.id = ts.capsule_id
    """).fetchall()

    for r in rows:
        if r["trust"] < threshold:
            continue
        for link in s.links_from(r["id"]):
            if link["type"] != derive_from:
                continue
            target = link["target"]
            with s.conn:
                cur = s.conn.execute("""
                    INSERT OR IGNORE INTO links (source, type, target, metadata)
                    VALUES (?, ?, ?, ?)
                """, (r["id"], rel, target, json.dumps({
                    "derived_by": rule_id, "trust": round(r["trust"], 6)
                })))
                if cur.rowcount:
                    _log_fire(s, rule_id, r["id"], rel, target,
                              extra={"trust": round(r["trust"], 6)})
                    fired.append((rule_id, r["id"], rel, target))

    return fired, warnings


def _eval_kind_and_age(s, rule_id, condition, effect):
    """Condition: {type: kind_and_age, kind, min_age_days, age_field?, via_link?}.
    Effect: {relationship, derive_from?}.
    Fires when a capsule of the given kind is older than min_age_days,
    optionally only if reached via a specific inbound link type."""
    kind       = condition.get("kind")
    min_age    = float(condition.get("min_age_days", 7))
    age_field  = condition.get("age_field")
    via_link   = condition.get("via_link")
    rel        = effect.get("relationship")
    derive_from = effect.get("derive_from")

    if not (kind and rel):
        return [], [f"{rule_id}: kind_and_age needs 'kind' and 'relationship'"]
    if derive_from and not via_link:
        return [], [f"{rule_id}: kind_and_age with derive_from needs 'via_link'"]

    fired, warnings = [], []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    rows = s.conn.execute("""
        SELECT id, state_json, created_at FROM capsules
        WHERE is_meta = 0 AND json_extract(state_json, '$.kind') = ?
    """, (kind,)).fetchall()

    for r in rows:
        state = json.loads(r["state_json"])

        # Determine age: prefer state field if given, else created_at
        age_days = None
        if age_field and state.get(age_field):
            try:
                anchor = datetime.fromisoformat(str(state[age_field]).replace(" ", "T"))
                if anchor.tzinfo is not None:
                    anchor = anchor.replace(tzinfo=None)
                age_days = (now - anchor).total_seconds() / 86400.0
            except Exception:
                pass
        if age_days is None:
            try:
                created = datetime.fromisoformat(r["created_at"].replace(" ", "T"))
                age_days = (now - created).total_seconds() / 86400.0
            except Exception:
                continue

        if age_days < min_age:
            continue

        if via_link:
            sources = s.conn.execute(
                "SELECT source FROM links WHERE target=? AND type=?",
                (r["id"], via_link)
            ).fetchall()
            for src in sources:
                src_id = src["source"]
                with s.conn:
                    cur = s.conn.execute("""
                        INSERT OR IGNORE INTO links (source, type, target, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (src_id, rel, r["id"], json.dumps({
                        "derived_by": rule_id,
                        "age_days": round(age_days, 1),
                    })))
                    if cur.rowcount:
                        _log_fire(s, rule_id, src_id, rel, r["id"],
                                  extra={"age_days": round(age_days, 1)})
                        fired.append((rule_id, src_id, rel, r["id"]))
        else:
            with s.conn:
                cur = s.conn.execute("""
                    INSERT OR IGNORE INTO links (source, type, target, metadata)
                    VALUES (?, ?, ?, ?)
                """, (rule_id, rel, r["id"], json.dumps({
                    "derived_by": rule_id,
                    "age_days": round(age_days, 1),
                })))
                if cur.rowcount:
                    _log_fire(s, rule_id, rule_id, rel, r["id"],
                              extra={"age_days": round(age_days, 1)})
                    fired.append((rule_id, rule_id, rel, r["id"]))

    return fired, warnings


def _leaf_features(s, capsule_id):
    """Return list of {pos, features} for token leaves in a subtree."""
    out = []
    stack = [capsule_id]
    seen = set()
    while stack:
        cid = stack.pop()
        if cid in seen:
            continue
        seen.add(cid)
        c = s.get(cid)
        if not c:
            continue
        if c["foundation"] == "foundation:token":
            out.append({"pos": c["state"].get("pos"),
                        "features": c["state"].get("features", {})})
        for l in s.links_from(cid):
            if l["type"] == "has-child":
                stack.append(l["target"])
    return out


def _sv_agree(s, np_cid, vp_cid):
    """Subject-verb agreement: NP head noun's number matches VP head verb's number."""
    nouns = [l for l in _leaf_features(s, np_cid) if l["pos"] == "noun"]
    verbs = [l for l in _leaf_features(s, vp_cid) if l["pos"] == "verb"]
    if not nouns or not verbs:
        return True
    np_num = nouns[-1]["features"].get("number")
    vp_num = verbs[0]["features"].get("number")
    if np_num and vp_num:
        return np_num == vp_num
    return True


def _subject_semantic_check(s, verb_cid, np_cid):
    """If verb has subject_must_be_animate, NP head noun must be animate."""
    verb = s.get(verb_cid)
    if not verb:
        return True
    if not verb["state"].get("features", {}).get("subject_must_be_animate"):
        return True
    nouns = [l for l in _leaf_features(s, np_cid) if l["pos"] == "noun"]
    if not nouns:
        return False
    animacy = nouns[-1]["features"].get("animacy")
    return animacy in ("animal", "human")


def _object_semantic_check(s, verb_cid, np_cid):
    """If verb has object_must_be_animate, NP head noun must be animate."""
    verb = s.get(verb_cid)
    if not verb:
        return True
    if not verb["state"].get("features", {}).get("object_must_be_animate"):
        return True
    nouns = [l for l in _leaf_features(s, np_cid) if l["pos"] == "noun"]
    if not nouns:
        return False
    animacy = nouns[-1]["features"].get("animacy")
    return animacy in ("animal", "human")


def _eval_sequence(s, rule_id, condition, effect, scope):
    """Condition: {match: [{foundation, state: {k: v}}, ...]}.
    Effect: {foundation, state: {k: v}}.
    Fires on adjacent spans; composes them into a new capsule."""
    patterns = condition.get("match", [])
    if not patterns:
        return [], [f"{rule_id}: sequence needs 'match'"]
    if not scope:
        return [], []

    # Collect candidates per pattern
    candidates = []
    scope_list = list(scope)
    placeholders = ",".join("?" * len(scope_list))

    for pat in patterns:
        foundation = pat.get("foundation")
        state_filter = pat.get("state", {})
        if foundation and not foundation.startswith("foundation:"):
            foundation = f"foundation:{foundation}"

        q = f"SELECT id, foundation, state_json FROM capsules WHERE is_meta=0 AND id IN ({placeholders})"
        args = scope_list[:]
        if foundation:
            q += " AND foundation = ?"
            args.append(foundation)

        rows = s.conn.execute(q, args).fetchall()
        matches = []
        for r in rows:
            state = json.loads(r["state_json"])
            if not all(state.get(k) == v for k, v in state_filter.items()):
                continue
            # Optional per-leaf feature filter (e.g. features: {transitive: false})
            if "features" in pat:
                pf = pat["features"]
                cf = state.get("features", {})
                if not all(cf.get(k) == v for k, v in pf.items()):
                    continue
            matches.append({"id": r["id"], "foundation": r["foundation"], "state": state})
        candidates.append(matches)

    def span(c):
        st = c["state"]
        if c["foundation"] == "foundation:token":
            i = st.get("index")
            return (i, i) if i is not None else None
        a, b = st.get("start"), st.get("end")
        return (a, b) if a is not None and b is not None else None

    handles = []
    def walk(pos, so_far, prev_end):
        if pos == len(candidates):
            handles.append(list(so_far))
            return
        for cand in candidates[pos]:
            sp = span(cand)
            if sp is None:
                continue
            st_, en_ = sp
            if prev_end is not None and st_ != prev_end + 1:
                continue
            so_far.append(cand)
            walk(pos + 1, so_far, en_)
            so_far.pop()

    walk(0, [], None)

    fired, warnings = [], []
    agree_mode = condition.get("number_agree")

    for handle in handles:
        if agree_mode:
            nums = [h["state"].get("features", {}).get("number") for h in handle]
            nums = [n for n in nums if n]
            if len(set(nums)) > 1:
                continue

        # Subject-verb agreement (opt-in per rule)
        if condition.get("subject_verb_agree") and len(handle) == 2:
            if not _sv_agree(s, handle[0]["id"], handle[1]["id"]):
                continue

        # Subject animacy: subject (handle[0] = NP) must satisfy VP's verb requirements
        if condition.get("subject_verb_agree") and len(handle) == 2:
            vp_children = s.conn.execute(
                "SELECT target FROM links WHERE source=? AND type='has-child' "
                "ORDER BY json_extract(metadata, '$.position')",
                (handle[1]["id"],)
            ).fetchall()
            if vp_children:
                verb_cid = vp_children[0]["target"]
                verb = s.get(verb_cid)
                if (verb and verb["foundation"] == "foundation:token"
                        and not _subject_semantic_check(s, verb_cid, handle[0]["id"])):
                    continue

        # Object semantic check: verb-with-animate-req + NP at positions 0,1.
        # Note: _object_semantic_check short-circuits if the verb has no
        # object_must_be_animate feature, so this is cheap for other rules.
        if (len(handle) >= 2
                and handle[0]["foundation"] == "foundation:token"
                and handle[1]["foundation"] == "foundation:phrase"
                and handle[1]["state"].get("category") == "NP"):
            if not _object_semantic_check(s, handle[0]["id"], handle[1]["id"]):
                continue

        sp_first = span(handle[0])
        sp_last = span(handle[-1])
        new_start, new_end = sp_first[0], sp_last[1]
        first_id = handle[0]["id"]
        session = first_id.split("/")[1] if first_id.startswith("parse/") else "anon"
        new_id = f"parse/{session}/{rule_id}/{new_start}-{new_end}"

        if s.get(new_id):
            continue

        new_foundation = effect.get("foundation", "phrase")
        if not new_foundation.startswith("foundation:"):
            new_foundation = f"foundation:{new_foundation}"
        new_state = dict(effect.get("state", {}))
        new_state["start"] = new_start
        new_state["end"] = new_end

        try:
            with s.conn:
                s.conn.execute(
                    "INSERT INTO capsules (id, foundation, state_json, is_meta) VALUES (?, ?, ?, 0)",
                    (new_id, new_foundation, json.dumps(new_state))
                )
                for i, child in enumerate(handle):
                    s.conn.execute(
                        "INSERT OR IGNORE INTO links (source, type, target, metadata) VALUES (?, 'has-child', ?, ?)",
                        (new_id, child["id"], json.dumps({"position": i}))
                    )
                s.conn.execute(
                    "INSERT INTO events (event_type, capsule_id, payload) VALUES ('rule.fired', ?, ?)",
                    (rule_id, json.dumps({"derived": new_id, "children": [c["id"] for c in handle]}))
                )
            fired.append((rule_id, "(sequence)", "has-child", new_id))
        except Exception as e:
            warnings.append(f"{rule_id}: failed to create {new_id}: {e}")

    return fired, warnings


def evaluate_rules(s: Substrate, scope=None, only_types=None):
    """Evaluate every rule. Idempotent. Returns (fired, warnings)."""
    fired, warnings = [], []

    for r in s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE foundation = 'foundation:rule'"
    ):
        rule_id = r["id"]
        state   = json.loads(r["state_json"])
        condition = state.get("condition")
        effect    = state.get("effect")

        if not condition or not effect:
            warnings.append(f"{rule_id}: missing condition/effect — skipped")
            continue

        ctype = condition.get("type", "pair")
        if only_types is not None and ctype not in only_types:
            continue

        if ctype == "trust_above":
            f, w = _eval_trust_above(s, rule_id, condition, effect)
        elif ctype == "kind_and_age":
            f, w = _eval_kind_and_age(s, rule_id, condition, effect)
        elif ctype == "sequence":
            if scope is None:
                continue
            f, w = _eval_sequence(s, rule_id, condition, effect, scope=scope)
        else:
            f, w = _eval_pair(s, rule_id, condition, effect)

        fired.extend(f)
        warnings.extend(w)

    return fired, warnings
