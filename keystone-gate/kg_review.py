"""Walk a person through cubes: proposals, empty lenses, validation, attestation.

Only a person's answers change anything. Blank input skips, so a session can
stop at any point and pick up where it left off.
"""
from kg_agent import (LENSES, accept_proposal, attest, completeness, fill_face,
                      list_cubes, list_proposals, reject_proposal, show_cube,
                      validate)


def _review_proposals(s, cube_id, by, ask, show):
    """Returns False if the person quit."""
    proposals = list_proposals(s, cube_id=cube_id, status="pending")
    accept_rest = False
    for p in proposals:
        show(f"\n  [{p.get('lens', 'neighbour')}] {p.get('content') or p.get('other_cube_id')}")
        answer = "a" if accept_rest else ask("  a=accept  r=reject  all=accept rest  q=quit, blank skips: ")
        answer = answer.strip().lower()
        if answer == "q":
            return False
        if answer == "all":
            accept_rest = True
            answer = "a"
        if answer == "a":
            accept_proposal(s, p["id"], accepted_by=by)
        elif answer == "r":
            reject_proposal(s, p["id"], rejected_by=by,
                            reason=ask("  reason, blank for none: ").strip() or None)
    return True


def _fill_empty_lenses(s, cube_id, ask, show):
    """Returns False if the person quit."""
    for lens in completeness(s, cube_id)["missing_lenses"]:
        text = ask(f"\n  {lens} in your words, q=quit, blank skips: ").strip()
        if text.lower() == "q":
            return False
        if text:
            fill_face(s, cube_id, lens, text)
    return True


def _validate_and_attest(s, cube_id, by, ask):
    state = completeness(s, cube_id)
    if not state["missing_lenses"] and not state["validated"]:
        note = ask("\n  Validate? Type a note to validate, blank skips: ").strip()
        if note:
            validate(s, cube_id, by, note=note)
    cube = show_cube(s, cube_id)
    attested = cube["attestation"] and not cube["attestation"].get("retracted_because")
    if cube["completeness"]["complete"] and not attested:
        if ask("\n  Do you stand behind this? y=attest, blank skips: ").strip().lower() == "y":
            attest(s, cube_id, by)


def review(s, by, cube_id=None, ask=input, show=print):
    """Review cubes that still need a person. Returns how many were looked at."""
    cubes = [c["id"] for c in list_cubes(s) if cube_id in (None, c["id"])]
    seen = 0
    for cid in cubes:
        data = show_cube(s, cid)
        attested = data["attestation"] and not data["attestation"].get("retracted_because")
        pending = list_proposals(s, cube_id=cid, status="pending")
        if data["completeness"]["complete"] and attested and not pending:
            continue
        seen += 1
        show(f"\n=== {cid}\n  {data['content']}")
        if not _review_proposals(s, cid, by, ask, show):
            return seen
        if not _fill_empty_lenses(s, cid, ask, show):
            return seen
        _validate_and_attest(s, cid, by, ask)
    return seen
