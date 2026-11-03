"""Entities, and sorting old capsules into entities and subjects.

An entity is a thing that exists. People are foundation:person, projects
foundation:project, and everything else foundation:entity, with a `kind`.

Older capsules were stored as plain knowledge. A sort proposal says what one
should become: an entity, a subject, merged into another capsule, or dropped.
Nothing changes until a person accepts it. See docs/VOCABULARY.md.

Renames, merges and drops write their SQL directly and log their own event in
the same transaction, as trust.py and rules.py do, since Substrate has no
rename. Old events keep the old id; the new event names it.
"""
import json
import re

from kg_cube import _now, _update_state

# Links between entities, and from an entity to a subject. Others already in
# the store, such as follows or declared-by, are left as they are.
RELATIONS = ["uses", "part-of", "owns", "building", "works-at", "at", "can"]
ACTIONS = ["entity", "subject", "merge", "drop", "describe"]


def slug(name):
    return "-".join(re.findall(r"[a-z0-9]+", name.lower())) or "unnamed"


def entity_foundation(kind):
    return {"person": "foundation:person", "project": "foundation:project"}.get(kind, "foundation:entity")


def entity_id(name, kind):
    prefix = kind if kind in ("person", "project") else "entity"
    return f"{prefix}/{slug(name)}"


def _event(conn, event_type, capsule_id, payload):
    conn.execute("INSERT INTO events (event_type, capsule_id, payload) VALUES (?, ?, ?)",
                 (event_type, capsule_id, json.dumps(payload)))


def _move_links(conn, old, new):
    """Point every link at or from old to new. A link new already has is dropped."""
    for col in ("source", "target"):
        conn.execute(f"UPDATE OR IGNORE links SET {col} = ? WHERE {col} = ?", (new, old))
    conn.execute("DELETE FROM links WHERE source = ? OR target = ?", (old, old))
    conn.execute("UPDATE OR IGNORE trust_scores SET capsule_id = ? WHERE capsule_id = ?", (new, old))


def rename(s, old, new, foundation=None, state=None):
    """Give a capsule a new id, and optionally a new foundation and state."""
    row = s.get(old)
    if not row:
        return {"error": f"{old} not found"}
    if s.get(new):
        return {"error": f"{new} already exists"}
    with s.conn:
        s.conn.execute("INSERT INTO capsules (id, foundation, state_json) VALUES (?, ?, ?)",
                       (new, foundation or row["foundation"], json.dumps(state or row["state"])))
        _move_links(s.conn, old, new)
        s.conn.execute("DELETE FROM capsules WHERE id = ?", (old,))
        _event(s.conn, "capsule.renamed", new, {"from": old, "foundation": foundation or row["foundation"]})
    return {"id": new}


def reclassify(s, cid, foundation, state):
    """Change a capsule's foundation in place, keeping its id."""
    if not s.get(cid):
        return {"error": f"{cid} not found"}
    with s.conn:
        s.conn.execute("UPDATE capsules SET foundation = ?, state_json = ?, updated_at = datetime('now') "
                       "WHERE id = ?", (foundation, json.dumps(state), cid))
        _event(s.conn, "capsule.reclassified", cid, {"foundation": foundation})
    return {"id": cid}


def merge(s, old, into):
    """Fold a duplicate into another capsule. The duplicate's state is kept in the event."""
    row, keep = s.get(old), s.get(into)
    if not row or not keep:
        return {"error": f"{old if not row else into} not found"}
    with s.conn:
        _move_links(s.conn, old, into)
        s.conn.execute("DELETE FROM capsules WHERE id = ?", (old,))
        _event(s.conn, "capsule.merged", into, {"from": old, "state": row["state"]})
    return {"id": into}


def drop(s, cid, reason):
    row = s.get(cid)
    if not row:
        return {"error": f"{cid} not found"}
    with s.conn:
        s.conn.execute("DELETE FROM links WHERE source = ? OR target = ?", (cid, cid))
        s.conn.execute("DELETE FROM capsules WHERE id = ?", (cid,))
        _event(s.conn, "capsule.deleted", cid, {"reason": reason, "state": row["state"]})
    return {"id": cid}


def _flip_used_in(s, subject_id):
    """`<subject> used-in <entity>` becomes `<entity> uses <subject>`."""
    with s.conn:
        for (target,) in s.conn.execute("SELECT target FROM links WHERE source = ? AND type = 'used-in'",
                                        (subject_id,)).fetchall():
            s.conn.execute("DELETE FROM links WHERE source = ? AND type = 'used-in' AND target = ?",
                           (subject_id, target))
            s.conn.execute("INSERT OR IGNORE INTO links (source, type, target) VALUES (?, 'uses', ?)",
                           (target, subject_id))
            _event(s.conn, "link.retyped", subject_id, {"target": target, "new_type": "uses", "reversed": True})


# --- Entities -------------------------------------------------------------

def add_entity(s, name, kind, by, **fields):
    eid = entity_id(name, kind)
    if s.get(eid):
        return {"error": f"{eid} already exists"}
    s.write({"id": eid, "foundation": entity_foundation(kind),
             "state": {"name": name, "kind": kind, "created_by": by, "created_at": _now(), **fields}})
    return {"id": eid}


def relate(s, source, relation, target):
    if relation not in RELATIONS:
        return {"error": f"relation must be one of: {', '.join(RELATIONS)}"}
    for cid in (source, target):
        if not s.get(cid):
            return {"error": f"{cid} not found"}
    s.link(source, relation, target)
    return {"source": source, "relation": relation, "target": target}


ENTITY_FOUNDATIONS = ("foundation:entity", "foundation:person", "foundation:project")


def list_entities(s):
    ph = ",".join("?" * len(ENTITY_FOUNDATIONS))
    rows = s.conn.execute(f"SELECT id, foundation, state_json FROM capsules WHERE is_meta = 0 "
                          f"AND foundation IN ({ph}) ORDER BY id", ENTITY_FOUNDATIONS).fetchall()
    return [{"id": r["id"], "foundation": r["foundation"], **json.loads(r["state_json"])} for r in rows]


# --- Sort proposals -------------------------------------------------------

def propose_sort(s, target, action, proposed_by, rationale=None, kind=None, new_id=None, name=None, into=None):
    """Suggest what an old capsule should become. Idempotent per target."""
    if action not in ACTIONS:
        return {"error": f"action must be one of: {', '.join(ACTIONS)}"}
    if not s.get(target):
        return {"error": f"{target} not found"}
    pid = f"proposal/sort/{target}"
    old = s.get(pid)
    state = {"kind": "sort-proposal", "target": target, "action": action, "entity_kind": kind,
             "new_id": new_id, "name": name, "into": into, "proposed_by": proposed_by,
             "rationale": rationale, "status": "pending", "proposed_at": _now()}
    if old and old["state"]["status"] == "accepted":
        return {"skipped": True, "reason": "already accepted", "proposal_id": pid}
    if old and old["state"]["status"] == "rejected" and \
            all(old["state"].get(k) == state[k] for k in ("action", "entity_kind", "new_id", "into")):
        return {"skipped": True, "reason": "previously rejected unchanged", "proposal_id": pid}
    s.write({"id": pid, "foundation": "foundation:knowledge", "state": state})
    return {"proposal_id": pid, "status": "pending"}


def list_sort_proposals(s, status="pending"):
    rows = s.conn.execute("SELECT id, state_json FROM capsules WHERE "
                          "json_extract(state_json, '$.kind') = 'sort-proposal' ORDER BY id").fetchall()
    out = [{"id": r["id"], **json.loads(r["state_json"])} for r in rows]
    return out if status == "any" else [p for p in out if p["status"] == status]


def _apply(s, p):
    target, action = p["target"], p["action"]
    state = s.get(target)["state"]
    name = p.get("name") or state.get("name") or target.split("/")[-1]
    if action == "entity":
        kind = p.get("entity_kind")
        new_state = {k: v for k, v in state.items() if k != "kind"} | {"name": name, "kind": kind}
        new_id = p.get("new_id") or target
        if new_id == target:
            return reclassify(s, target, entity_foundation(kind), new_state)
        return rename(s, target, new_id, entity_foundation(kind), new_state)
    if action == "subject":
        new_id = p.get("new_id") or f"subject/{slug(name)}"
        new_state = {k: v for k, v in state.items() if k != "kind"} | {"name": name, "kind": p.get("entity_kind")}
        r = rename(s, target, new_id, "foundation:subject", new_state) if new_id != target \
            else reclassify(s, target, "foundation:subject", new_state)
        if "error" not in r:
            _flip_used_in(s, new_id)
        return r
    if action == "merge":
        return merge(s, target, p["into"])
    if action == "drop":
        return drop(s, target, p.get("rationale") or "dropped on review")
    if action == "describe":
        # A document about an entity: `same-as` both ways becomes `<into> described-by <target>`
        with s.conn:
            s.conn.execute("DELETE FROM links WHERE type = 'same-as' AND ((source = ? AND target = ?) OR "
                           "(source = ? AND target = ?))", (target, p["into"], p["into"], target))
            s.conn.execute("INSERT OR IGNORE INTO links (source, type, target) VALUES (?, 'described-by', ?)",
                           (p["into"], target))
            _event(s.conn, "link.retyped", p["into"], {"target": target, "new_type": "described-by"})
        return {"id": target}
    return {"error": f"unknown action {action}"}


def accept_sort(s, proposal_id, by, **overrides):
    """Apply a sort proposal. overrides (action, entity_kind, new_id, name, into)
    let a person correct it while accepting."""
    p = s.get(proposal_id)
    if not p or p["state"].get("kind") != "sort-proposal":
        return {"error": f"sort proposal {proposal_id} not found"}
    st = p["state"]
    if st["status"] != "pending":
        return {"error": f"proposal status is {st['status']!r}, not pending"}
    applied = {**st, **{k: v for k, v in overrides.items() if v is not None}}
    if applied["action"] not in ACTIONS:
        return {"error": f"action must be one of: {', '.join(ACTIONS)}"}
    if applied["action"] == "entity" and not applied.get("entity_kind"):
        return {"error": "an entity needs a kind"}
    r = _apply(s, applied)
    if "error" in r:
        return r
    _update_state(s, proposal_id, {**applied, "status": "accepted", "accepted_by": by,
                                   "accepted_at": _now(), "result": r["id"]})
    return {"proposal_id": proposal_id, "action": applied["action"], "id": r["id"]}


def reject_sort(s, proposal_id, by, reason=None):
    p = s.get(proposal_id)
    if not p or p["state"].get("kind") != "sort-proposal":
        return {"error": f"sort proposal {proposal_id} not found"}
    if p["state"]["status"] != "pending":
        return {"error": f"proposal status is {p['state']['status']!r}, not pending"}
    _update_state(s, proposal_id, {**p["state"], "status": "rejected", "rejected_by": by,
                                   "rejected_at": _now(), "reason": reason})
    return {"proposal_id": proposal_id, "status": "rejected"}
