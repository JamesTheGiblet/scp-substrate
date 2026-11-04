"""Keystone Gate tests, part 2 of 3. Run: python tests/run.py"""
from support_kg import *


def test_cube_attestation_gating():
    from kg_agent import create_cube, fill_face, validate, attestation_eligible, LENSES
    s = _fresh_kg_substrate()
    try:
        r = create_cube(s, "test cube")
        cid = r["cube_id"]
        assert attestation_eligible(s, cid) is False
        for i, lens in enumerate(LENSES):
            fill_face(s, cid, lens, f"content {i}")
        assert attestation_eligible(s, cid) is False
        validate(s, cid, "james")
        assert attestation_eligible(s, cid) is True
    finally:
        s.close()


def test_face_change_voids_validation():
    from kg_agent import fill_face, attestation_eligible, completeness, show_cube
    s = _fresh_kg_substrate()
    try:
        cid = _complete_cube(s)
        assert attestation_eligible(s, cid) is True
        fill_face(s, cid, "FACT", "something else entirely")
        comp = completeness(s, cid)
        assert comp["validated"] is False and comp["complete"] is False, comp
        assert abs(comp["score"] - 0.80) < 1e-6, comp
        assert attestation_eligible(s, cid) is False
        assert "FACT changed" in show_cube(s, cid)["validation"]["stale_because"]
    finally:
        s.close()


def test_refill_with_same_content_keeps_validation():
    from kg_agent import fill_face, attestation_eligible
    s = _fresh_kg_substrate()
    try:
        cid = _complete_cube(s)
        fill_face(s, cid, "FACT", "FACT content")
        assert attestation_eligible(s, cid) is True
    finally:
        s.close()


def test_revalidation_clears_stale():
    from kg_agent import fill_face, validate, attestation_eligible
    s = _fresh_kg_substrate()
    try:
        cid = _complete_cube(s)
        fill_face(s, cid, "FACT", "changed")
        validate(s, cid, "james", note="reviewed the change")
        assert attestation_eligible(s, cid) is True
    finally:
        s.close()


def test_agent_edits_are_event_logged():
    """Updates go through Substrate.write, so nothing skips the ledger."""
    from kg_agent import (create_cube, fill_face, validate, propose_face,
                          reject_proposal, set_contradicts)
    s = _fresh_kg_substrate()

    def written(cid):
        return s.conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='capsule.written' AND capsule_id=?",
            (cid,),
        ).fetchone()[0]

    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        face = fill_face(s, a, "FACT", "one")["face_id"]
        fill_face(s, a, "FACT", "two")
        assert written(face) == 2

        v = validate(s, a, "james")["face_id"]
        validate(s, a, "james")
        assert written(v) == 2

        pid = propose_face(s, a, "COUNTER", "x", proposed_by="r")["proposal_id"]
        propose_face(s, a, "COUNTER", "y", proposed_by="r")
        reject_proposal(s, pid, "james")
        assert written(pid) == 3

        set_contradicts(s, a, b)
        assert written(a) == 2
    finally:
        s.close()


def test_attest_requires_complete_cube():
    from kg_agent import create_cube, attest
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        assert "error" in attest(s, cid, "james")
        assert s.get(f"{cid}/attestation") is None
    finally:
        s.close()


def test_attestation_raises_fused_trust():
    from kg_agent import attest
    from trust import fused_trust
    s = _fresh_kg_substrate()
    try:
        cid = _complete_cube(s)
        before = fused_trust(s, cid)["posterior"]
        assert "error" not in attest(s, cid, "james")
        assert fused_trust(s, cid)["posterior"] > before + 0.1
    finally:
        s.close()


def test_face_change_retracts_attestation():
    from kg_agent import attest, fill_face, validate
    from trust import fused_trust
    s = _fresh_kg_substrate()
    try:
        cid = _complete_cube(s)
        before = fused_trust(s, cid)["posterior"]
        attest(s, cid, "james")
        fill_face(s, cid, "FACT", "changed")
        assert abs(fused_trust(s, cid)["posterior"] - before) < 1e-9
        assert s.get(f"{cid}/attestation")["state"]["retracted_because"]
        assert "error" in attest(s, cid, "james")
        validate(s, cid, "james")
        assert "error" not in attest(s, cid, "james")
        assert fused_trust(s, cid)["posterior"] > before + 0.1
    finally:
        s.close()


def test_review_takes_a_cube_to_attested():
    from kg_agent import show_cube
    from kg_review import review
    s = _fresh_kg_substrate()
    try:
        cid = _draft_cube(s)
        review(s, "james", ask=_answers("all", "my view", "looks right", "y"),
               show=lambda text: None)
        data = show_cube(s, cid)
        assert data["completeness"]["complete"] is True, data
        assert data["faces"]["OPINION"]["filled_by"] == "human", data
        assert data["validation"]["validator"] == "james", data
        assert data["attestation"]["source"] == "james", data
    finally:
        s.close()


def test_review_blank_answers_change_nothing():
    from kg_agent import completeness, list_proposals
    from kg_review import review
    s = _fresh_kg_substrate()
    try:
        cid = _draft_cube(s)
        review(s, "james", ask=_answers("", "", "", "", "", "", "", "", ""),
               show=lambda text: None)
        assert completeness(s, cid)["score"] == 0.0
        assert len(list_proposals(s, cube_id=cid, status="pending")) == 4
    finally:
        s.close()


def test_review_quit_stops_and_keeps_answers():
    from kg_agent import completeness, list_proposals
    from kg_review import review
    s = _fresh_kg_substrate()
    try:
        cid = _draft_cube(s)
        review(s, "james", ask=_answers("a", "r", "", "q"), show=lambda text: None)
        assert completeness(s, cid)["filled_lenses"] == ["FACT"]
        assert len(list_proposals(s, cube_id=cid, status="rejected")) == 1
        assert len(list_proposals(s, cube_id=cid, status="pending")) == 2
    finally:
        s.close()


def test_seed_cubes_are_drafts_not_decisions():
    """Seeds propose only: no face, validation or attestation is written."""
    import seed_cubes
    from kg_agent import LENSES
    assert len(seed_cubes.CUBES) >= 20
    assert len({c["id"] for c in seed_cubes.CUBES}) == len(seed_cubes.CUBES)
    assert "OPINION" not in seed_cubes.LENSES
    for cube in seed_cubes.CUBES:
        assert all(cube[lens] for lens in seed_cubes.LENSES), cube["id"]
        assert "OPINION" not in cube, cube["id"]


def test_cube_invalid_lens():
    from kg_agent import create_cube, fill_face
    s = _fresh_kg_substrate()
    try:
        r = create_cube(s, "test cube")
        cid = r["cube_id"]
        bad = fill_face(s, cid, "NOT_A_LENS", "content")
        assert "error" in bad
    finally:
        s.close()


def test_cube_contradicts():
    from kg_agent import create_cube, set_contradicts
    s = _fresh_kg_substrate()
    try:
        r1 = create_cube(s, "the sky is blue")
        r2 = create_cube(s, "the sky is green")
        r = set_contradicts(s, r1["cube_id"], r2["cube_id"], note="colour disagreement")
        assert "error" not in r
        c = s.get(r1["cube_id"])
        assert c["state"]["contradicts"]["other"] == r2["cube_id"]
        link = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='contradicts' AND target=?",
            (r1["cube_id"], r2["cube_id"]),
        ).fetchone()
        assert link
    finally:
        s.close()


# --- neighbour tests -----------------------------------------------------
def test_neighbour_link_bidirectional():
    from kg_agent import create_cube, link_neighbour
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        r = link_neighbour(s, a, b, note="related")
        assert "error" not in r
        # Both directions exist
        forward = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='neighbour' AND target=?",
            (a, b),
        ).fetchone()
        backward = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='neighbour' AND target=?",
            (b, a),
        ).fetchone()
        assert forward and backward
    finally:
        s.close()


def test_neighbour_link_missing_cube():
    from kg_agent import create_cube, link_neighbour
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        r = link_neighbour(s, a, "cube/does-not-exist")
        assert "error" in r
    finally:
        s.close()


def test_neighbour_list():
    from kg_agent import create_cube, link_neighbour, list_neighbours
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        link_neighbour(s, a, b)
        r = list_neighbours(s, a)
        assert b in r["neighbours"], r
        r2 = list_neighbours(s, b)
        assert a in r2["neighbours"], r2
    finally:
        s.close()


# --- proposal tests ------------------------------------------------------
def test_propose_face():
    from kg_agent import create_cube, propose_face, list_proposals
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        r = propose_face(s, cid, "FACT", "the sky is blue", proposed_by="test_rule")
        assert "error" not in r, r
        assert r["status"] == "created"
        props = list_proposals(s, cube_id=cid, status="pending")
        assert len(props) == 1
        assert props[0]["lens"] == "FACT"
        assert props[0]["content"] == "the sky is blue"
    finally:
        s.close()


def test_propose_face_idempotent():
    from kg_agent import create_cube, propose_face, list_proposals
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        r1 = propose_face(s, cid, "FACT", "first version", proposed_by="rule")
        r2 = propose_face(s, cid, "FACT", "second version", proposed_by="rule")
        assert r1["proposal_id"] == r2["proposal_id"]
        assert r2["status"] == "updated"
        props = list_proposals(s, cube_id=cid)
        assert len(props) == 1
        assert props[0]["content"] == "second version"
    finally:
        s.close()


def test_propose_face_skips_filled_lens():
    from kg_agent import create_cube, fill_face, propose_face
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        fill_face(s, cid, "FACT", "already filled")
        r = propose_face(s, cid, "FACT", "would be newer", proposed_by="rule")
        assert r.get("skipped") is True
    finally:
        s.close()


def test_accept_proposal_fills_face():
    from kg_agent import (create_cube, propose_face, accept_proposal,
                          completeness, list_proposals)
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        r = propose_face(s, cid, "FACT", "the sky is blue", proposed_by="rule")
        pid = r["proposal_id"]
        acc = accept_proposal(s, pid, accepted_by="james")
        assert "error" not in acc, acc
        assert acc["status"] == "accepted"
        # Face now exists
        face = s.get(f"{cid}/face/FACT")
        assert face is not None
        assert face["state"]["content"] == "the sky is blue"
        # Completeness moved
        comp = completeness(s, cid)
        assert abs(comp["score"] - 0.16) < 1e-6
        # Proposal is no longer pending
        pending = list_proposals(s, cube_id=cid, status="pending")
        assert len(pending) == 0
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
