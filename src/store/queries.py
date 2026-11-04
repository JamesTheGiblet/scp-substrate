"""Reasoning queries against sc.db. All read the substrate, none mutate it."""
import math
from datetime import datetime, timezone


def what_supports(s, claim_id):
    """Direct support links pointing at a claim."""
    return s.conn.execute("""
        SELECT c.id, c.foundation, c.state_json
        FROM capsules c
        JOIN links l ON l.target = c.id
        WHERE l.source = ? AND l.type IN ('supported-by', 'derived-from')
    """, (claim_id,)).fetchall()


def observations(s):
    return s.by_foundation("foundation:observation")


def why_trusted(s, model_id):
    return s.conn.execute("""
        SELECT l.type, l.target, c.foundation,
               json_extract(c.state_json, '$.rationale') AS rationale
        FROM links l
        JOIN capsules c ON c.id = l.target
        WHERE l.source = ? AND l.type IN ('justified-by', 'applies-to', 'grounded-in')
    """, (model_id,)).fetchall()


def trust_now(s, capsule_id):
    """Current trust, decayed from the materialised score to now."""
    row = s.conn.execute("""
        SELECT c.id, ts.score, ts.computed_at,
               json_extract(c.state_json, '$.n0') AS n0,
               json_extract(c.state_json, '$.k') AS k,
               json_extract(c.state_json, '$.age_days') AS age_days
        FROM capsules c
        JOIN trust_scores ts ON ts.capsule_id = c.id
        WHERE c.id = ?
    """, (capsule_id,)).fetchone()
    if not row:
        return None

    try:
        computed = datetime.fromisoformat(row["computed_at"].replace(" ", "T"))
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_days = max(0.0, (now - computed).total_seconds() / 86400.0)
    except Exception:
        elapsed_days = 0.0

    k = float(row["k"]) if row["k"] is not None else 0.0
    current = row["score"] * math.exp(-k * elapsed_days)

    return {
        "id": row["id"],
        "score": current,
        "materialized_score": row["score"],
        "computed_at": row["computed_at"],
        "elapsed_days": elapsed_days,
        "n0": row["n0"],
        "k": k,
    }


def verified(s, capsule_id):
    """Return verification records for a capsule."""
    import json as _j
    rows = s.conn.execute("""
        SELECT c.id, c.state_json, c.created_at
        FROM capsules c
        JOIN links l ON l.source = c.id
        WHERE l.type = 'verifies' AND l.target = ?
        ORDER BY c.created_at DESC
    """, (capsule_id,)).fetchall()
    out = []
    for r in rows:
        state = _j.loads(r["state_json"])
        out.append({"id": r["id"], "at": r["created_at"], **state})
    return out


def latest(s, capsule_id):
    """Follow the supersedes chain forward to the most recent version."""
    current = capsule_id
    seen = set()
    while current not in seen:
        seen.add(current)
        row = s.conn.execute(
            "SELECT source FROM links WHERE target=? AND type='supersedes'",
            (current,)
        ).fetchone()
        if not row:
            return current
        current = row["source"]
    return current  # cycle guard
