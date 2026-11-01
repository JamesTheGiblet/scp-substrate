"""Cube-as-agent. The base unit of Keystone Gate.

A cube is a record whose six faces are filled by lenses and validated by
humans. Five lenses at 16% each plus human validation at 20% = 100%.
Completeness gates attestation: no trust until a cube is complete.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))

from substrate import Substrate


LENSES = ["FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"]
LENS_WEIGHT = 0.16
HUMAN_VALIDATION_WEIGHT = 0.20
TOTAL_WEIGHT = LENS_WEIGHT * len(LENSES) + HUMAN_VALIDATION_WEIGHT


def _slugify(text):
    """First few words, alphanumerics only, for a stable cube id."""
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "unnamed"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _update_state(s, capsule_id, state):
    """Replace a capsule's state through Substrate.write, so the event is logged."""
    s.write({
        "id": capsule_id,
        "foundation": s.get(capsule_id)["foundation"],
        "state": state,
    })


def create_cube(s, content, source=None, tags=None, cube_id=None):
    """Create a new cube capsule. Returns {cube_id} or {error}."""
    if not cube_id:
        base = _slugify(content)
        candidate = f"cube/{base}"
        i = 2
        while s.get(candidate):
            candidate = f"cube/{base}-{i}"
            i += 1
        cube_id = candidate

    if s.get(cube_id):
        return {"error": f"cube {cube_id} already exists"}

    s.write({
        "id": cube_id,
        "foundation": "foundation:cube",
        "state": {
            "kind": "cube",
            "content": content,
            "source": source,
            "tags": tags or [],
            "contradicts": None,
            "created_at": _now(),
        },
    })
    try:
        s.link(cube_id, "classified-by", "default-cube")
    except Exception:
        pass
    return {"cube_id": cube_id}


def fill_face(s, cube_id, lens, content, confidence=None, filled_by="human"):
    """Fill one lens face of a cube. Returns {face_id, lens} or {error}."""
    if lens not in LENSES:
        return {"error": f"invalid lens {lens!r}; must be one of {LENSES}"}
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}

    face_id = f"{cube_id}/face/{lens}"
    state = {
        "kind": "cube-face",
        "cube_id": cube_id,
        "lens": lens,
        "content": content,
        "confidence": confidence,
        "filled_by": filled_by,
        "filled_at": _now(),
    }
    existing = s.get(face_id)
    if existing:
        _update_state(s, face_id, state)
        if existing["state"].get("content") != content:
            _mark_validation_stale(s, cube_id, lens)
    else:
        s.write({
            "id": face_id,
            "foundation": "foundation:cube-face",
            "state": state,
        })
        s.link(cube_id, "has-face", face_id)
        s.link(face_id, "about", cube_id)
    return {"face_id": face_id, "lens": lens}


def _mark_validation_stale(s, cube_id, lens):
    """A human validated what the cube said then. Changing a face voids that."""
    face_id = f"{cube_id}/face/human-validation"
    face = s.get(face_id)
    if face:
        _update_state(s, face_id, {**face["state"], "stale": True,
                                   "stale_because": f"{lens} changed at {_now()}"})


def validate(s, cube_id, validator, note=None):
    """Record human validation of a cube. Returns {face_id, validator} or {error}."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}

    face_id = f"{cube_id}/face/human-validation"
    state = {
        "kind": "cube-face",
        "cube_id": cube_id,
        "lens": "HUMAN_VALIDATION",
        "validator": validator,
        "note": note,
        "validated_at": _now(),
    }
    existing = s.get(face_id)
    if existing:
        _update_state(s, face_id, state)
    else:
        s.write({
            "id": face_id,
            "foundation": "foundation:cube-face",
            "state": state,
        })
        s.link(cube_id, "has-face", face_id)
        s.link(face_id, "about", cube_id)
    return {"face_id": face_id, "validator": validator}


def set_contradicts(s, cube_id, other_cube_id, note=None):
    """Flag that this cube contradicts another."""
    c = s.get(cube_id)
    if not c:
        return {"error": f"cube {cube_id} not found"}
    if not s.get(other_cube_id):
        return {"error": f"other cube {other_cube_id} not found"}
    new_state = dict(c["state"])
    new_state["contradicts"] = {"other": other_cube_id, "note": note, "set_at": _now()}
    _update_state(s, cube_id, new_state)
    if not s.conn.execute(
        "SELECT 1 FROM links WHERE source=? AND type='contradicts' AND target=?",
        (cube_id, other_cube_id),
    ).fetchone():
        s.link(cube_id, "contradicts", other_cube_id)
    return {"cube_id": cube_id, "contradicts": other_cube_id}


def completeness(s, cube_id):
    """Return completeness score and face state."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}

    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules "
        "WHERE foundation = 'foundation:cube-face' "
        "  AND json_extract(state_json, '$.cube_id') = ?",
        (cube_id,),
    ).fetchall()

    filled = []
    validated = False
    for r in rows:
        st = json.loads(r["state_json"])
        lens = st.get("lens")
        if lens == "HUMAN_VALIDATION":
            validated = not st.get("stale")
        elif lens in LENSES:
            filled.append(lens)

    missing = [l for l in LENSES if l not in filled]
    score = len(filled) * LENS_WEIGHT + (HUMAN_VALIDATION_WEIGHT if validated else 0)

    return {
        "cube_id": cube_id,
        "score": round(score, 4),
        "filled_lenses": filled,
        "missing_lenses": missing,
        "validated": validated,
        "complete": score >= 0.9999,
    }


def attestation_eligible(s, cube_id):
    """True only if completeness == 1.0. Completeness gates attestation."""
    c = completeness(s, cube_id)
    if "error" in c:
        return False
    return c["complete"]


def show_cube(s, cube_id):
    """Return full cube data for rendering."""
    c = s.get(cube_id)
    if not c:
        return {"error": f"cube {cube_id} not found"}
    comp = completeness(s, cube_id)

    faces = {}
    for lens in LENSES:
        fid = f"{cube_id}/face/{lens}"
        f = s.get(fid)
        faces[lens] = f["state"] if f else None

    vfid = f"{cube_id}/face/human-validation"
    vf = s.get(vfid)
    validation = vf["state"] if vf else None

    return {
        "cube_id": cube_id,
        "content": c["state"].get("content"),
        "source": c["state"].get("source"),
        "tags": c["state"].get("tags"),
        "contradicts": c["state"].get("contradicts"),
        "created_at": c["state"].get("created_at"),
        "faces": faces,
        "validation": validation,
        "completeness": comp,
    }


def list_cubes(s):
    rows = s.conn.execute(
        "SELECT id FROM capsules WHERE foundation = 'foundation:cube' AND is_meta = 0 ORDER BY id"
    ).fetchall()
    out = []
    for r in rows:
        comp = completeness(s, r["id"])
        out.append({
            "id": r["id"],
            "score": comp["score"] if "score" in comp else 0,
            "complete": comp.get("complete", False),
        })
    return out


def link_neighbour(s, cube_a, cube_b, note=None):
    """Create a bidirectional neighbour relationship between two cubes.

    Neighbours know only IDs; they query the ledger for detail. That's why
    we only link — we don't copy state. The relationship is stored as
    two directed `neighbour` links (a->b and b->a) so traversal works
    from either end without special-casing direction.
    """
    for cid in (cube_a, cube_b):
        if not s.get(cid):
            return {"error": f"cube {cid} not found"}

    if cube_a == cube_b:
        return {"error": "cannot link a cube to itself"}

    for src, tgt in ((cube_a, cube_b), (cube_b, cube_a)):
        existing = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='neighbour' AND target=?",
            (src, tgt),
        ).fetchone()
        if not existing:
            s.link(src, "neighbour", tgt)

    return {"cube_a": cube_a, "cube_b": cube_b, "note": note}


def list_neighbours(s, cube_id):
    """Return cube IDs directly neighboured to a cube."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    rows = s.conn.execute(
        "SELECT target FROM links WHERE source=? AND type='neighbour' ORDER BY target",
        (cube_id,),
    ).fetchall()
    return {"cube": cube_id, "neighbours": [r["target"] for r in rows]}


# --- Proposal mechanism -------------------------------------------------
# The agent proposes; humans decide. A proposal is a capsule that describes
# an action to take on a cube. Accepting a proposal calls the corresponding
# primitive (fill_face or link_neighbour). Rejecting it marks it rejected
# and leaves the cube unchanged.
#
# Proposals are idempotent per (cube, lens) for face type and per
# unordered cube pair for neighbour type. Running the same rule twice does
# not create duplicate proposals — it updates the pending one in place.


def _face_proposals(s, cube_id, lens):
    """Return every proposal for (cube, lens), any status."""
    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE "
        "  json_extract(state_json, '$.kind') = 'cube-proposal' AND "
        "  json_extract(state_json, '$.proposal_type') = 'face' AND "
        "  json_extract(state_json, '$.cube_id') = ? AND "
        "  json_extract(state_json, '$.lens') = ?",
        (cube_id, lens),
    ).fetchall()
    return [{"id": r["id"], **json.loads(r["state_json"])} for r in rows]


def _neighbour_proposals(s, cube_id, other_cube_id):
    """Return every proposal for the pair, either direction, any status."""
    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE "
        "  json_extract(state_json, '$.kind') = 'cube-proposal' AND "
        "  json_extract(state_json, '$.proposal_type') = 'neighbour' AND "
        "  ((json_extract(state_json, '$.cube_id') = ? AND "
        "    json_extract(state_json, '$.other_cube_id') = ?) OR "
        "   (json_extract(state_json, '$.cube_id') = ? AND "
        "    json_extract(state_json, '$.other_cube_id') = ?))",
        (cube_id, other_cube_id, other_cube_id, cube_id),
    ).fetchall()
    return [{"id": r["id"], **json.loads(r["state_json"])} for r in rows]


def _next_proposal_id(s, cube_id):
    n = 1
    while s.get(f"{cube_id}/proposal/{n}"):
        n += 1
    return f"{cube_id}/proposal/{n}"


def propose_face(s, cube_id, lens, content, proposed_by, rationale=None, confidence=None):
    """Propose filling one lens of a cube. Idempotent on (cube, lens)."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    if lens not in LENSES:
        return {"error": f"invalid lens {lens!r}; must be one of {LENSES}"}

    # If lens already filled, no need to propose
    existing_face = s.get(f"{cube_id}/face/{lens}")
    if existing_face:
        return {"skipped": True, "reason": "lens already filled", "lens": lens}

    proposals = _face_proposals(s, cube_id, lens)

    # Rejection sticks: if ever rejected with identical content, skip.
    # If rejected but content differs, allow a new proposal
    # (the rule has new information the human hasn't seen yet).
    for p in proposals:
        if p.get("status") == "rejected" and p.get("content") == content:
            return {"skipped": True,
                    "reason": "previously rejected with same content",
                    "lens": lens,
                    "proposal_id": p["id"]}

    for p in proposals:
        if p.get("status") == "pending":
            new_state = dict(p)
            del new_state["id"]
            new_state["content"] = content
            new_state["rationale"] = rationale
            new_state["confidence"] = confidence
            new_state["proposed_by"] = proposed_by
            new_state["proposed_at"] = _now()
            _update_state(s, p["id"], new_state)
            return {"proposal_id": p["id"], "lens": lens, "status": "updated"}

    pid = _next_proposal_id(s, cube_id)
    s.write({
        "id": pid,
        "foundation": "foundation:knowledge",
        "state": {
            "kind": "cube-proposal",
            "proposal_type": "face",
            "cube_id": cube_id,
            "lens": lens,
            "content": content,
            "proposed_by": proposed_by,
            "rationale": rationale,
            "confidence": confidence,
            "status": "pending",
            "proposed_at": _now(),
        },
    })
    s.link(pid, "about", cube_id)
    return {"proposal_id": pid, "lens": lens, "status": "created"}


def propose_neighbour(s, cube_id, other_cube_id, proposed_by, rationale=None):
    """Propose linking two cubes as neighbours. Idempotent on the pair."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    if not s.get(other_cube_id):
        return {"error": f"other cube {other_cube_id} not found"}
    if cube_id == other_cube_id:
        return {"error": "cannot propose a cube as its own neighbour"}

    # If link already exists, no need to propose
    existing_link = s.conn.execute(
        "SELECT 1 FROM links WHERE source=? AND type='neighbour' AND target=?",
        (cube_id, other_cube_id),
    ).fetchone()
    if existing_link:
        return {"skipped": True, "reason": "neighbour link already exists"}

    proposals = _neighbour_proposals(s, cube_id, other_cube_id)

    # Rejection sticks: if ever rejected for the same rationale, skip, whichever
    # cube the rule runs from. A new rationale (more shared tags) is new
    # information the human hasn't seen yet.
    for p in proposals:
        if p.get("status") == "rejected" and p.get("rationale") == rationale:
            return {"skipped": True,
                    "reason": "previously rejected with same rationale",
                    "other_cube_id": other_cube_id,
                    "proposal_id": p["id"]}

    for p in proposals:
        if p.get("status") == "pending":
            new_state = dict(p)
            del new_state["id"]
            new_state["rationale"] = rationale
            new_state["proposed_by"] = proposed_by
            new_state["proposed_at"] = _now()
            _update_state(s, p["id"], new_state)
            return {"proposal_id": p["id"], "other_cube_id": other_cube_id, "status": "updated"}

    pid = _next_proposal_id(s, cube_id)
    s.write({
        "id": pid,
        "foundation": "foundation:knowledge",
        "state": {
            "kind": "cube-proposal",
            "proposal_type": "neighbour",
            "cube_id": cube_id,
            "other_cube_id": other_cube_id,
            "proposed_by": proposed_by,
            "rationale": rationale,
            "status": "pending",
            "proposed_at": _now(),
        },
    })
    s.link(pid, "about", cube_id)
    return {"proposal_id": pid, "other_cube_id": other_cube_id, "status": "created"}


def list_proposals(s, cube_id=None, status="pending"):
    """List proposal capsules. Optional cube_id filter. status='pending'|'accepted'|'rejected'|'any'."""
    query = "SELECT id, state_json FROM capsules WHERE json_extract(state_json, '$.kind') = 'cube-proposal'"
    params = []
    if cube_id:
        query += " AND json_extract(state_json, '$.cube_id') = ?"
        params.append(cube_id)
    if status != "any":
        query += " AND json_extract(state_json, '$.status') = ?"
        params.append(status)
    query += " ORDER BY id"

    rows = s.conn.execute(query, params).fetchall()
    return [{"id": r["id"], **json.loads(r["state_json"])} for r in rows]


def accept_proposal(s, proposal_id, accepted_by):
    """Accept a proposal: dispatch to fill_face or link_neighbour, mark accepted."""
    proposal = s.get(proposal_id)
    if not proposal:
        return {"error": f"proposal {proposal_id} not found"}
    st = proposal["state"]
    if st.get("status") != "pending":
        return {"error": f"proposal status is {st.get('status')!r}, not pending"}

    ptype = st.get("proposal_type")

    if ptype == "face":
        applied = fill_face(
            s, st["cube_id"], st["lens"], st["content"],
            confidence=st.get("confidence"),
            filled_by=f"proposal:{st.get('proposed_by', '?')} (accepted by {accepted_by})",
        )
    elif ptype == "neighbour":
        applied = link_neighbour(
            s, st["cube_id"], st["other_cube_id"],
            note=f"proposed by {st.get('proposed_by', '?')}, accepted by {accepted_by}",
        )
    else:
        return {"error": f"unknown proposal_type {ptype!r}"}

    if "error" in applied:
        return applied

    new_state = dict(st)
    new_state["status"] = "accepted"
    new_state["accepted_by"] = accepted_by
    new_state["accepted_at"] = _now()
    new_state["applied"] = applied
    _update_state(s, proposal_id, new_state)
    return {"proposal_id": proposal_id, "status": "accepted", "applied": applied}


def reject_proposal(s, proposal_id, rejected_by, reason=None):
    """Reject a proposal: mark it rejected. Cube unchanged."""
    proposal = s.get(proposal_id)
    if not proposal:
        return {"error": f"proposal {proposal_id} not found"}
    st = proposal["state"]
    if st.get("status") != "pending":
        return {"error": f"proposal status is {st.get('status')!r}, not pending"}

    new_state = dict(st)
    new_state["status"] = "rejected"
    new_state["rejected_by"] = rejected_by
    new_state["rejected_at"] = _now()
    new_state["rejection_reason"] = reason
    _update_state(s, proposal_id, new_state)
    return {"proposal_id": proposal_id, "status": "rejected"}
