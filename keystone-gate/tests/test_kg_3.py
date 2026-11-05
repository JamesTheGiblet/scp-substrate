"""Keystone Gate tests, part 3 of 3. Run: python tests/run.py"""
from support_kg import *


def test_reject_proposal_leaves_cube_unchanged():
    from kg_agent import (create_cube, propose_face, reject_proposal,
                          completeness, list_proposals)
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        r = propose_face(s, cid, "FACT", "the sky is green", proposed_by="rule")
        pid = r["proposal_id"]
        rej = reject_proposal(s, pid, rejected_by="james", reason="wrong colour")
        assert rej["status"] == "rejected"
        # Face still empty
        assert s.get(f"{cid}/face/FACT") is None
        # Completeness still zero
        comp = completeness(s, cid)
        assert comp["score"] == 0.0
        # Not pending, but is rejected
        rejected = list_proposals(s, cube_id=cid, status="rejected")
        assert len(rejected) == 1
        assert rejected[0]["rejection_reason"] == "wrong colour"
    finally:
        s.close()


def test_propose_neighbour():
    from kg_agent import create_cube, propose_neighbour, accept_proposal
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        r = propose_neighbour(s, a, b, proposed_by="rule", rationale="shared tag")
        assert "error" not in r, r
        pid = r["proposal_id"]
        acc = accept_proposal(s, pid, accepted_by="james")
        assert acc["status"] == "accepted"
        # Link now exists
        link = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='neighbour' AND target=?",
            (a, b),
        ).fetchone()
        assert link
    finally:
        s.close()


def test_rule_fact_from_decision():
    from kg_agent import create_cube, list_proposals
    from kg_rules import run_rules
    s = _seed_decision_substrate()
    try:
        cid = create_cube(s, "SQLite decision for the substrate")["cube_id"]
        run_rules(s, cid, only_rules=["fact_from_decision"])
        props = list_proposals(s, cube_id=cid, status="pending")
        fact_props = [p for p in props if p["lens"] == "FACT"]
        assert len(fact_props) == 1
        assert "SQLite" in fact_props[0]["content"]
        assert fact_props[0]["proposed_by"] == "fact_from_decision"
    finally:
        s.close()


def test_rule_counter_from_alternatives():
    from kg_agent import create_cube, list_proposals
    from kg_rules import run_rules
    s = _seed_decision_substrate()
    try:
        cid = create_cube(s, "SQLite decision")["cube_id"]
        run_rules(s, cid, only_rules=["counter_from_alternatives"])
        props = list_proposals(s, cube_id=cid, status="pending")
        counter = [p for p in props if p["lens"] == "COUNTER"]
        assert len(counter) == 1
        assert "Postgres" in counter[0]["content"]
        assert "DuckDB" in counter[0]["content"]
    finally:
        s.close()


def test_rule_neighbour_on_subject():
    from kg_agent import create_cube, list_proposals
    from kg_rules import run_rules
    s = _seed_decision_substrate()
    try:
        with s.conn:
            s.conn.execute("INSERT OR IGNORE INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES ('foundation:subject', 'foundation:foundation', '{}', 1)")
        s.write({"id": "subject/mg90s", "foundation": "foundation:subject", "state": {"name": "MG90S"}})
        a = create_cube(s, "The servo stalls when its current spikes.", tags=["needs-check"])["cube_id"]
        b = create_cube(s, "A stalled servo draws its peak current.", tags=["needs-check"])["cube_id"]
        c = create_cube(s, "The servo horn is plastic.", tags=["needs-check"])["cube_id"]
        d = create_cube(s, "Peak current stalls the regulator.", tags=["needs-check"])["cube_id"]
        for cid in (a, b, c):
            s.link(cid, "about-subject", "subject/mg90s")
        run_rules(s, a, only_rules=["neighbour_on_subject"])
        neigh = [p for p in list_proposals(s, cube_id=a, status="pending") if p.get("proposal_type") == "neighbour"]
        # b shares the subject and two words; c only the subject; d only words; a shared tag counts for nothing
        assert [p["other_cube_id"] for p in neigh] == [b], neigh
        assert neigh[0]["rationale"].startswith("both about MG90S, and both say "), neigh
    finally:
        s.close()

def test_rule_skips_filled_lens():
    from kg_agent import create_cube, fill_face
    from kg_rules import run_rules
    s = _seed_decision_substrate()
    try:
        cid = create_cube(s, "SQLite decision")["cube_id"]
        fill_face(s, cid, "FACT", "manually filled first")
        # Rule tries to propose FACT, must skip because lens is filled
        results = run_rules(s, cid, only_rules=["fact_from_decision"])
        # Either skipped or empty; no new pending FACT proposals
        from kg_agent import list_proposals
        props = list_proposals(s, cube_id=cid, status="pending")
        fact_props = [p for p in props if p["lens"] == "FACT"]
        assert len(fact_props) == 0
    finally:
        s.close()


def test_run_rules_idempotent():
    from kg_agent import create_cube, list_proposals
    from kg_rules import run_rules
    s = _seed_decision_substrate()
    try:
        cid = create_cube(s, "SQLite decision")["cube_id"]
        run_rules(s, cid)
        first = list_proposals(s, cube_id=cid, status="pending")
        run_rules(s, cid)
        second = list_proposals(s, cube_id=cid, status="pending")
        assert len(first) == len(second)
    finally:
        s.close()


def test_rejection_sticks():
    """Rejecting a proposal prevents re-proposal of identical content."""
    from kg_agent import create_cube, propose_face, reject_proposal, list_proposals
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        r1 = propose_face(s, cid, "FACT", "the sky is green", proposed_by="rule_a")
        reject_proposal(s, r1["proposal_id"], rejected_by="james", reason="wrong colour")
        # Rule runs again — same content, should be skipped
        r2 = propose_face(s, cid, "FACT", "the sky is green", proposed_by="rule_a")
        assert r2.get("skipped") is True, r2
        # No pending proposals
        pending = list_proposals(s, cube_id=cid, status="pending")
        assert len(pending) == 0
    finally:
        s.close()


def test_rejection_sticks_past_nine_proposals():
    """Proposal 10 sorts before proposal 9 as text; rejections must not care."""
    from kg_agent import create_cube, propose_face, reject_proposal
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        for i in range(11):
            pid = propose_face(s, cid, "FACT", f"v{i}", proposed_by="rule")["proposal_id"]
            reject_proposal(s, pid, rejected_by="james")
        for i in range(11):
            r = propose_face(s, cid, "FACT", f"v{i}", proposed_by="rule")
            assert r.get("skipped") is True, (i, r)
    finally:
        s.close()


def test_earlier_rejection_still_sticks():
    """A rejected, B rejected, A proposed again: A stays rejected."""
    from kg_agent import create_cube, propose_face, reject_proposal
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        for content in ("a", "b"):
            pid = propose_face(s, cid, "FACT", content, proposed_by="rule")["proposal_id"]
            reject_proposal(s, pid, rejected_by="james")
        assert propose_face(s, cid, "FACT", "a", proposed_by="rule").get("skipped") is True
    finally:
        s.close()


def test_neighbour_rejection_sticks_both_directions():
    from kg_agent import create_cube, propose_neighbour, reject_proposal, list_proposals
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        pid = propose_neighbour(s, a, b, proposed_by="rule")["proposal_id"]
        reject_proposal(s, pid, rejected_by="james")
        assert propose_neighbour(s, a, b, proposed_by="rule").get("skipped") is True
        assert propose_neighbour(s, b, a, proposed_by="rule").get("skipped") is True
        assert list_proposals(s, status="pending") == []
    finally:
        s.close()


def test_neighbour_rejection_allows_new_rationale():
    from kg_agent import create_cube, propose_neighbour, reject_proposal
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        pid = propose_neighbour(s, a, b, proposed_by="rule",
                                rationale="shared tags: ['x']")["proposal_id"]
        reject_proposal(s, pid, rejected_by="james")
        r = propose_neighbour(s, b, a, proposed_by="rule",
                              rationale="shared tags: ['x', 'y']")
        assert r.get("status") == "created", r
    finally:
        s.close()


def test_neighbour_proposal_idempotent_both_directions():
    from kg_agent import create_cube, propose_neighbour, list_proposals
    s = _fresh_kg_substrate()
    try:
        a = create_cube(s, "cube a")["cube_id"]
        b = create_cube(s, "cube b")["cube_id"]
        r1 = propose_neighbour(s, a, b, proposed_by="rule")
        r2 = propose_neighbour(s, b, a, proposed_by="rule")
        assert r1["proposal_id"] == r2["proposal_id"], (r1, r2)
        assert len(list_proposals(s, status="pending")) == 1
    finally:
        s.close()


def test_decision_match_ignores_shared_english_words():
    from kg_rules import _find_decision_for
    s = _seed_decision_substrate()
    try:
        for text in ("the code ran on a single machine", "a mode of transport",
                     "my file is lost", "I chose pizza for dinner"):
            assert _find_decision_for(s, text) is None, text
        assert _find_decision_for(s, "SQLite decision")["id"] == "chose-sqlite"
        assert _find_decision_for(s, "a single file database")["id"] == "chose-sqlite"
    finally:
        s.close()


def test_decision_match_picks_strongest_overlap():
    from kg_rules import _find_decision_for
    s = _seed_decision_substrate()
    try:
        s.write({"id": "chose-rust", "foundation": "foundation:knowledge",
                 "state": {"kind": "decision", "decision": "Rust for the firmware toolchain"}})
        s.write({"id": "chose-rust-builds", "foundation": "foundation:knowledge",
                 "state": {"kind": "decision", "decision": "Rust for firmware toolchain builds"}})
        hit = _find_decision_for(s, "rust firmware toolchain builds")
        assert hit["id"] == "chose-rust-builds", hit
    finally:
        s.close()


def test_rejection_allows_new_content():
    """Rejected but different content → allowed through."""
    from kg_agent import create_cube, propose_face, reject_proposal, list_proposals
    s = _fresh_kg_substrate()
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        r1 = propose_face(s, cid, "FACT", "the sky is green", proposed_by="rule_a")
        reject_proposal(s, r1["proposal_id"], rejected_by="james", reason="wrong colour")
        # New content — should be allowed
        r2 = propose_face(s, cid, "FACT", "the sky is blue", proposed_by="rule_a")
        assert r2.get("status") == "created", r2
        pending = list_proposals(s, cube_id=cid, status="pending")
        assert len(pending) == 1
        assert pending[0]["content"] == "the sky is blue"
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
