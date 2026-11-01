"""Sequence rules: reduce adjacent parse nodes into phrases."""
import json


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
                        "features": c["state"].get("features", {}),
                        "index": c["state"].get("index")})
        for l in s.links_from(cid):
            if l["type"] == "has-child":
                stack.append(l["target"])
    # Sort by token index to preserve left-to-right order. Without this,
    # _sv_agree / _object_semantic_check / _subject_semantic_check all
    # read the wrong "head" on compound nouns.
    out.sort(key=lambda x: x["index"] if x.get("index") is not None else 9999)
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
    # Permissive: missing/unknown animacy passes. Only explicit object/abstract blocks.
    if animacy is None:
        return True
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
    # Permissive: missing/unknown animacy passes. Only explicit object/abstract blocks.
    if animacy is None:
        return True
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
