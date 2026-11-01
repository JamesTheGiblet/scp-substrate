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
            except (TypeError, ValueError):
                # Unreadable date: fall back to the capsule's own age
                age_days = age_days
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


from rules_sequence import _eval_sequence




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
