"""Proposals. Rules and drafts suggest changes to cubes; humans decide."""
import json

from store.claim_links import WORDS, relate, word_of
from kg_cube import LENSES, _now, _update_state, fill_face, link_neighbour


# --- Proposal mechanism -------------------------------------------------
# The agent proposes; humans decide. A proposal is a capsule that describes
# an action to take on a cube. Accepting a proposal calls the corresponding
# primitive (fill_face or link_neighbour). Rejecting it marks it rejected
# and leaves the cube unchanged.
#
# Proposals are idempotent per (cube, lens) for face type and per
# unordered cube pair for neighbour type. Running the same rule twice does
# not create duplicate proposals — it updates the pending one in place.

# The connecting words a link can carry, so it reads as a sentence:
# "<from cube> protects <other cube>". Kept short so they mean the same each time.
CONNECTING_WORDS = list(WORDS)


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


def accept_proposal(s, proposal_id, accepted_by, word=None, reverse=False):
    """Accept a proposal: dispatch to fill_face or link_neighbour, mark accepted.

    A neighbour link can carry a connecting word, which then becomes the link
    itself. It reads from the proposal's cube to the other one, or the other
    way round when reverse is set.
    """
    proposal = s.get(proposal_id)
    if not proposal:
        return {"error": f"proposal {proposal_id} not found"}
    st = proposal["state"]
    if st.get("status") != "pending":
        return {"error": f"proposal status is {st.get('status')!r}, not pending"}

    ptype = st.get("proposal_type")
    # An older word, such as depends on, is read as the one that replaced it
    word = word_of(word) or word if word is not None else None
    if word is not None and (ptype != "neighbour" or word not in CONNECTING_WORDS):
        return {"error": f"connecting word must be one of: {', '.join(CONNECTING_WORDS)}"}

    if ptype == "face":
        applied = fill_face(
            s, st["cube_id"], st["lens"], st["content"],
            confidence=st.get("confidence"),
            filled_by=f"proposal:{st.get('proposed_by', '?')} (accepted by {accepted_by})",
        )
    elif ptype == "neighbour" and word:
        a, b = (st["other_cube_id"], st["cube_id"]) if reverse else (st["cube_id"], st["other_cube_id"])
        applied = relate(s, a, word, b, accepted_by, note=st.get("rationale"))
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
    if word:
        new_state["word"] = word
        new_state["from"] = st["other_cube_id"] if reverse else st["cube_id"]
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
