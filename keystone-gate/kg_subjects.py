"""Subjects: what claims are about. Proposed, then accepted by a person.

A subject exists once, as subject/<slug>. A claim (cube) links to it with
`about-subject`. Subjects never form on their own: a proposal names the subject and
the claims it would gather, and a person accepts, renames, narrows or rejects
it. See docs/VOCABULARY.md.
"""
import json
import re

from kg_cube import _now, _update_state
from store.kinds import IS_A

# Not plain `about`: trust.py reads an `about` link as marking a trust record,
# so a cube with one would lose its trust score.
ABOUT = "about-subject"


def _slug(name):
    return "-".join(re.findall(r"[a-z0-9]+", name.lower())) or "unnamed"


def _proposal_id(slug):
    return f"proposal/subject/{slug}"


def propose_subject(s, name, members, proposed_by, kind=None, rationale=None):
    """Propose a subject and the claims it would gather. Idempotent per name.

    A pending proposal is updated in place. A rejected one stays rejected
    unless the name's members or rationale change.
    """
    slug = _slug(name)
    if s.get(f"subject/{slug}"):
        return {"skipped": True, "reason": f"subject/{slug} already exists"}
    missing = [m for m in members if not s.get(m)]
    if missing:
        return {"error": f"claims not found: {', '.join(missing)}"}
    pid = _proposal_id(slug)
    old = s.get(pid)
    state = {"kind": "subject-proposal", "name": name, "subject_kind": kind,
             "members": sorted(set(members)), "proposed_by": proposed_by,
             "rationale": rationale, "status": "pending", "proposed_at": _now()}
    if old:
        st = old["state"]
        if st["status"] == "accepted":
            return {"skipped": True, "reason": "already accepted", "proposal_id": pid}
        if st["status"] == "rejected" and st["members"] == state["members"] \
                and st.get("rationale") == rationale:
            return {"skipped": True, "reason": "previously rejected unchanged", "proposal_id": pid}
    s.write({"id": pid, "foundation": "foundation:knowledge", "state": state})
    return {"proposal_id": pid, "status": "pending"}


def list_subject_proposals(s, status="pending"):
    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE "
        "json_extract(state_json, '$.kind') = 'subject-proposal' ORDER BY id").fetchall()
    out = [{"id": r["id"], **json.loads(r["state_json"])} for r in rows]
    return out if status == "any" else [p for p in out if p["status"] == status]


def accept_subject(s, proposal_id, by, name=None, members=None):
    """Create the subject and link its claims to it. name and members, if given,
    override the proposal's, so a person can rename or narrow it."""
    p = s.get(proposal_id)
    if not p or p["state"].get("kind") != "subject-proposal":
        return {"error": f"subject proposal {proposal_id} not found"}
    st = p["state"]
    if st["status"] != "pending":
        return {"error": f"proposal status is {st['status']!r}, not pending"}
    name = name or st["name"]
    members = st["members"] if members is None else members
    stray = sorted(set(members) - set(st["members"]))
    if stray:
        return {"error": f"not in the proposal: {', '.join(stray)}; add them after with add_claim"}
    subject_id = f"subject/{_slug(name)}"
    if s.get(subject_id):
        return {"error": f"{subject_id} already exists"}
    s.write({"id": subject_id, "foundation": "foundation:subject", "state": {
        "name": name, "kind": st.get("subject_kind"), "created_by": by,
        "created_at": _now(), "from_proposal": proposal_id}})
    for m in members:
        s.link(m, ABOUT, subject_id)
    _update_state(s, proposal_id, {**st, "status": "accepted", "accepted_by": by,
                                   "accepted_at": _now(), "subject_id": subject_id,
                                   "accepted_members": sorted(members)})
    return {"subject_id": subject_id, "members": sorted(members)}


def reject_subject(s, proposal_id, by, reason=None):
    p = s.get(proposal_id)
    if not p or p["state"].get("kind") != "subject-proposal":
        return {"error": f"subject proposal {proposal_id} not found"}
    if p["state"]["status"] != "pending":
        return {"error": f"proposal status is {p['state']['status']!r}, not pending"}
    _update_state(s, proposal_id, {**p["state"], "status": "rejected", "rejected_by": by,
                                   "rejected_at": _now(), "reason": reason})
    return {"proposal_id": proposal_id, "status": "rejected"}


def add_claim(s, cube_id, subject_id):
    """Say a claim is about an existing subject."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    subject = s.get(subject_id)
    if not subject or subject["foundation"] != "foundation:subject":
        return {"error": f"subject {subject_id} not found"}
    s.link(cube_id, ABOUT, subject_id)
    return {"cube_id": cube_id, "subject_id": subject_id}


def missing_subject(s, subject_ids):
    """The first id that is not a subject, or None."""
    for sid in subject_ids:
        row = s.get(sid)
        if not row or row["foundation"] != "foundation:subject":
            return sid
    return None


def list_subjects(s):
    """Every subject with the claims about it."""
    out = []
    for subj in s.by_foundation("foundation:subject"):
        claims = sorted(l["source"] for l in s.links_to(subj["id"], ABOUT))
        kinds = sorted(l["target"] for l in s.links_from(subj["id"]) if l["type"] == IS_A)
        out.append({"id": subj["id"], **subj["state"], "claims": claims, "is_a": kinds})
    return sorted(out, key=lambda x: x["id"])


def kind_of(s, subject_id, broader, by, kind=None):
    """Say a subject is a kind of a broader one, given by id or name. A name
    that isn't a subject yet is made into one, as an outline would."""
    from store.kinds import is_a
    bid = broader if broader.startswith("subject/") else f"subject/{_slug(broader)}"
    if not s.get(bid):
        if broader.startswith("subject/"):
            return {"error": f"subject {bid} not found"}
        pid = propose_subject(s, broader, [], by, kind=kind,
                              rationale=f"Named by {by} as a broader kind of {subject_id}")["proposal_id"]
        accept_subject(s, pid, by)
    return is_a(s, subject_id, bid, by)


def subjects_of(s, cube_id):
    return sorted(l["target"] for l in s.links_from(cube_id)
                  if l["type"] == ABOUT)
