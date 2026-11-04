"""Explicit user feedback → trust updates. The learning loop."""
import json
from store.substrate import Substrate


def apply_feedback(s, session_id, positive):
    """Walk a parse session; bump trust for its words and rules."""
    prefix = f"parse/{session_id}/%"

    # Words used
    word_rows = s.conn.execute("""
        SELECT json_extract(state_json, '$.text') AS word
        FROM capsules
        WHERE id LIKE ? AND foundation = 'foundation:token'
    """, (prefix,)).fetchall()
    words = sorted(set(r["word"] for r in word_rows))

    # Rules that fired (via rule.fired events with this session in payload)
    rule_rows = s.conn.execute("""
        SELECT capsule_id FROM events
        WHERE event_type = 'rule.fired' AND payload LIKE ?
    """, (f'%"derived":"parse/{session_id}/%',)).fetchall()
    rules = sorted(set(r["capsule_id"] for r in rule_rows))

    delta = 1 if positive else -1

    # Words → trust/freq/<word>
    w_updated, w_new = 0, 0
    for word in words:
        tid = f"trust/freq/{word}"
        existing = s.get(tid)
        if existing:
            cur = existing["state"].get("n0", 0)
            new_n0 = max(0, cur + delta)
            with s.conn:
                s.conn.execute(
                    "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                    (json.dumps({**existing["state"], "n0": new_n0}), tid)
                )
            w_updated += 1
        else:
            s.write({"id": tid, "foundation": "foundation:leighton-weight",
                     "state": {"n0": max(0, delta), "k": 0, "word": word}})
            w_new += 1

    # Rules → trust/rule/<short>
    r_updated, r_new = 0, 0
    for rule_id in rules:
        short = rule_id.split("/")[-1]
        tid = f"trust/rule/{short}"
        existing = s.get(tid)
        if existing:
            cur = existing["state"].get("n0", 0)
            new_n0 = max(0, cur + delta)
            with s.conn:
                s.conn.execute(
                    "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                    (json.dumps({**existing["state"], "n0": new_n0}), tid)
                )
            r_updated += 1
        else:
            s.write({"id": tid, "foundation": "foundation:leighton-weight",
                     "state": {"n0": max(0, delta), "k": 0, "rule": rule_id}})
            r_new += 1

    with s.conn:
        s.conn.execute(
            "INSERT INTO events (event_type, payload) VALUES ('feedback.applied', ?)",
            (json.dumps({"session": session_id, "positive": positive,
                         "words": words, "rules": rules}),)
        )

    return {"session": session_id, "positive": positive,
            "words_updated": w_updated, "words_new": w_new,
            "rules_updated": r_updated, "rules_new": r_new}
