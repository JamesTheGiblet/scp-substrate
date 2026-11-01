"""Boundary tests for Keystone Gate.

These tests use real data (not :memory:) because the boundary is the whole
point — we're proving Keystone Gate can query the substrate's foundations.
They run on a temporary copy of sc.db, so they can never write to the live one.
"""
import atexit
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

import substrate
from substrate import Substrate
from kg_stats import stats, count_by_foundation
from kg_router import route_list


def _use_copy_of_live_db():
    """Point every default Substrate() at a throwaway backup of sc.db."""
    tmp = tempfile.mkdtemp(prefix="kg-test-")
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    path = os.path.join(tmp, "sc.db")
    live = sqlite3.connect(_here.parent / "sc.db")
    copy = sqlite3.connect(path)
    with copy:
        live.backup(copy)
    live.close()
    copy.close()
    substrate.Substrate.__init__.__defaults__ = (path,)


_use_copy_of_live_db()


def test_foundations_exist():
    """The four KG foundations must be present in the substrate."""
    s = Substrate()
    try:
        for fid in [
            "foundation:cube",
            "foundation:lens",
            "foundation:cube-face",
            "foundation:neighbour",
        ]:
            row = s.get(fid)
            assert row is not None, f"{fid} missing"
            assert row["is_meta"] is True, f"{fid} must have is_meta=True"
    finally:
        s.close()


def test_default_cube_corrected():
    """default-cube must have the 5-lens shape."""
    s = Substrate()
    try:
        st = s.get("default-cube")["state"]
        assert st["lenses"] == ["FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"], st["lenses"]
        assert st["contradicts_field"] is True
        assert st["weighting"]["per_lens"] == 0.16
        assert st["weighting"]["human_validation"] == 0.20
    finally:
        s.close()


def test_stats_counts_kg_content():
    """kg_stats counts what is stored, with neighbours as link pairs."""
    st = stats()
    assert set(st.keys()) == {"cubes", "lenses", "cube_faces", "neighbours"}
    for k, v in st.items():
        assert isinstance(v, int), f"{k} should be int, got {type(v)}"
        assert v >= 0, f"{k} should be non-negative"
    s = Substrate()
    try:
        links = s.conn.execute(
            "SELECT COUNT(*) FROM links WHERE type='neighbour'"
        ).fetchone()[0]
    finally:
        s.close()
    assert st["neighbours"] * 2 == links, (st, links)


def test_route_list_runs():
    """kg_router.route_list works even with no neighbours."""
    result = route_list()
    assert isinstance(result, list), result


def test_boundary_imports():
    """kg modules import without errors."""
    from kg_stats import stats as _s
    from kg_router import route_list as _r
    from kg_agent import __doc__ as _a
    from kg_gate import __doc__ as _g
    from kg_hal import __doc__ as _h
    assert _s and _r


# --- gate tests ----------------------------------------------------------
def test_sc_capsule_exists():
    """The sc/symlm-answerer capsule must be seeded."""
    s = Substrate()
    try:
        sc = s.get("sc/symlm-answerer")
        assert sc is not None, "sc/symlm-answerer missing"
        assert sc["state"]["kind"] == "sc"
        assert len(sc["state"]["must"]) >= 2
        assert len(sc["state"]["test_cases"]) >= 2
    finally:
        s.close()


def test_gate_passes_good_answer():
    """A real answer that references real entities passes the gate."""
    from kg_hal import ask_gated
    from kg_gate import load_sc
    s = Substrate()
    try:
        sc = load_sc(s)
        result = ask_gated(s, "who is james", sc=sc)
        assert not result.get("rejected"), result
        assert "answer" in result, result
    finally:
        s.close()


def test_gate_rejects_invented_id():
    """A result mentioning a nonexistent slashed ID is rejected."""
    from kg_gate import check, load_sc
    s = Substrate()
    try:
        sc = load_sc(s)
        fake_result = {
            "ok": True,
            "summary": "Found this",
            "detail": "  -> contains -> made-up/repo/xyz",
            "intent": "intent/what-is",
            "entity": None,
        }
        compliance = check(s, {"input": "test", "result": fake_result}, sc=sc)
        assert not compliance["ok"], compliance
        assert any(v["rule"] == "no_invented_ids" for v in compliance["violations"])
        assert any("made-up/repo/xyz" in v["detail"] for v in compliance["violations"])
    finally:
        s.close()


def test_gate_rejects_invented_entity():
    """A result whose entity is not a real capsule is rejected."""
    from kg_gate import check, load_sc
    s = Substrate()
    try:
        sc = load_sc(s)
        fake_result = {
            "ok": True,
            "summary": "Nothing here",
            "detail": None,
            "intent": "intent/what-is",
            "entity": "totally-fake-entity-xyz",
        }
        compliance = check(s, {"input": "test", "result": fake_result}, sc=sc)
        assert not compliance["ok"], compliance
        assert any(v["rule"] == "no_invented_ids" for v in compliance["violations"])
    finally:
        s.close()


def test_gate_rejects_hallucinated_trust():
    """A result claiming a trust score that doesn't match is rejected."""
    from kg_gate import check, load_sc
    s = Substrate()
    try:
        sc = load_sc(s)
        fake_result = {
            "ok": True,
            "summary": "scp-claim is trusted (score 0.1234)",
            "detail": None,
            "intent": "intent/why-trusted",
            "entity": "scp-claim",
        }
        compliance = check(s, {"input": "test", "result": fake_result}, sc=sc)
        assert not compliance["ok"], compliance
        assert any(v["rule"] == "no_hallucinated_trust" for v in compliance["violations"])
    finally:
        s.close()


def test_gate_no_intent_is_compliant():
    """No intent matched → no answer → nothing to gate → passes."""
    from kg_gate import check, load_sc
    s = Substrate()
    try:
        sc = load_sc(s)
        compliance = check(s, {"input": "test", "result": None}, sc=sc)
        assert compliance["ok"], compliance
    finally:
        s.close()


def _gate(result):
    """Run a fake answer through the live contract. Returns violated rule names."""
    from kg_gate import check, load_sc
    s = Substrate()
    try:
        answer = {"ok": True, "intent": "intent/what-is", "entity": None, **result}
        compliance = check(s, {"input": "test", "result": answer}, sc=load_sc(s))
        return [v["rule"] for v in compliance["violations"]]
    finally:
        s.close()


def test_gate_rejects_invented_slug():
    assert "no_hallucinated_entities" in _gate({"summary": "santa-claus is real."})


def test_gate_rejects_invented_name():
    assert "no_hallucinated_entities" in _gate({"summary": "Written by Santa Claus."})


def test_gate_rejects_uppercase_slashed_id():
    assert "no_invented_ids" in _gate({"summary": "see repo/Fake/Thing"})


def test_gate_rejects_fragment_of_real_id():
    """Grounding matches whole terms, not substrings of stored content."""
    assert "no_invented_ids" in _gate({"summary": "see repo/jamesthegiblet"})


def test_gate_rejects_whole_number_trust():
    r = _gate({"summary": "scp-claim has trust 2.0", "entity": "scp-claim"})
    assert "no_hallucinated_trust" in r, r


def test_gate_rejects_capitalised_trust_label():
    r = _gate({"summary": "Trust: 0.1234", "entity": "scp-claim"})
    assert "no_hallucinated_trust" in r, r


def test_gate_rejects_answer_without_provenance():
    r = _gate({"summary": "The sky is blue.", "intent": None})
    assert r == ["no_llm_prior"], r


def test_gate_rejects_fake_intent():
    r = _gate({"summary": "The sky is blue.", "intent": "intent/made-up"})
    assert "no_llm_prior" in r, r


def test_gate_allows_refusal_without_intent():
    r = _gate({"ok": False, "summary": "I couldn't identify that.", "intent": None})
    assert r == [], r


def test_gate_passes_file_paths_in_stored_content():
    """A where-is answer cites paths, which are not capsule IDs."""
    from kg_gate import check, load_sc
    s = Substrate()
    try:
        path = s.conn.execute(
            "SELECT json_extract(state_json, '$.path') AS p FROM capsules "
            "WHERE json_extract(state_json, '$.kind') = 'source-file' "
            "  AND json_extract(state_json, '$.path') LIKE '%/%' LIMIT 1"
        ).fetchone()["p"]
        answer = {"ok": True, "intent": "intent/where-is", "entity": None,
                  "summary": "1 match(es):", "detail": f"  {path}:10 [function] x"}
        compliance = check(s, {"input": "x", "result": answer}, sc=load_sc(s))
        assert compliance["ok"], compliance
    finally:
        s.close()


def test_is_x_signed_finds_namespaced_capsule():
    from ask import answer_question
    s = Substrate()
    try:
        r = answer_question(s, "is james-gilbert-v1 signed")
        assert r["entity"] == "giblets-forge/author/james-gilbert-v1", r
        assert r["intent"] == "intent/verified", r
        assert answer_question(s, "what is signed-not-trusted")["intent"] == "intent/what-is"
    finally:
        s.close()


def test_gate_ignores_logged_chat_as_grounding():
    """Typing a name into `scps talk` must not make it real."""
    from kg_gate import _grounded_terms
    s = Substrate()
    try:
        s.write({"id": "turn/fake", "foundation": "foundation:knowledge",
                 "state": {"kind": "conversation-turn", "text": "ask about zaphod-beeblebrox"}})
        assert "zaphod-beeblebrox" not in _grounded_terms(s)
    finally:
        s.close()


def test_gate_fails_closed_on_unknown_must_not_rule():
    from kg_gate import check
    s = Substrate()
    try:
        sc = {"name": "t", "must": [], "must_not": [{"rule": "not_a_rule"}]}
        compliance = check(s, {"input": "x", "result": {"ok": True, "summary": "x"}}, sc=sc)
        assert not compliance["ok"], compliance
    finally:
        s.close()


# --- Claude tests --------------------------------------------------------
class _FakeResponse:
    def __init__(self, text, stop_reason="end_turn"):
        import types
        self.stop_reason = stop_reason
        self.content = [types.SimpleNamespace(type="text", text=text)]


class _FakeClient:
    """Stands in for anthropic.Anthropic(). Records requests; no network."""
    def __init__(self, claims=None, stop_reason="end_turn", error=None):
        import json, types
        self.calls = []
        text = json.dumps({"claims": claims or []})

        def create(**kwargs):
            self.calls.append(kwargs)
            if error:
                raise error
            return _FakeResponse(text, stop_reason)

        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=create))


def _claude(client, question="who is james"):
    from kg_llm import ask_claude
    s = Substrate()
    try:
        return ask_claude(s, question, client=client)
    finally:
        s.close()


GOOD_CLAIM = {"text": "James is a builder.", "evidence": "is a person — builder"}


def test_claude_answer_passes_when_anchored():
    client = _FakeClient([GOOD_CLAIM])
    r = _claude(client)
    assert r["source"] == "claude" and r["answer"] == "James is a builder.", r
    sent = client.calls[0]["messages"][0]["content"]
    assert "is a person" in sent and "who is james" in sent, sent


def test_claude_invented_quote_falls_back():
    r = _claude(_FakeClient([{"text": "James is a pilot.", "evidence": "is a pilot"}]))
    assert r["source"] == "walker" and "gate refused" in r["fallback_reason"], r
    assert "builder" in r["answer"], r
    assert any(v["rule"] == "claims_quote_evidence" for v in r["refused"]["violations"]), r


def test_claude_unsourced_number_falls_back():
    r = _claude(_FakeClient([{"text": "James has 12 projects.",
                              "evidence": "is a person — builder"}]))
    assert r["source"] == "walker", r
    assert any("12" in v["detail"] for v in r["refused"]["violations"]), r


def test_claude_unsourced_name_falls_back():
    r = _claude(_FakeClient([{"text": "James works with Bigfoot.",
                              "evidence": "is a person — builder"}]))
    assert r["source"] == "walker", r
    assert any("Bigfoot" in v["detail"] for v in r["refused"]["violations"]), r


def test_claude_no_claims_falls_back():
    assert _claude(_FakeClient([]))["source"] == "walker"


def test_claude_refusal_falls_back():
    r = _claude(_FakeClient([GOOD_CLAIM], stop_reason="refusal"))
    assert r["source"] == "walker" and "refusal" in r["fallback_reason"], r


def test_claude_api_error_falls_back():
    r = _claude(_FakeClient(error=RuntimeError("network down")))
    assert r["source"] == "walker" and "network down" in r["fallback_reason"], r
    assert "builder" in r["answer"], r


def test_claude_not_called_without_facts():
    client = _FakeClient([GOOD_CLAIM])
    assert _claude(client, "who is santa claus").get("answer") is not None
    assert _claude(client, "how do magnets work").get("no_intent") is True
    assert client.calls == [], client.calls


# --- cube tests ----------------------------------------------------------
def _fresh_kg_substrate():
    """In-memory substrate with KG foundations + default-cube."""
    from substrate import Substrate
    s = Substrate(":memory:")
    s.conn.executescript((_here.parent / "schema.sql").read_text())
    import json as _j
    with s.conn:
        for fid in ["foundation:foundation", "foundation:knowledge",
                    "foundation:cube", "foundation:lens", "foundation:cube-face",
                    "foundation:neighbour"]:
            s.conn.execute(
                "INSERT INTO capsules (id, foundation, state_json, is_meta) "
                "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,)
            )
        s.conn.execute(
            "INSERT INTO capsules (id, foundation, state_json) VALUES "
            "('default-cube', 'foundation:knowledge', ?)",
            (_j.dumps({"kind": "datacube",
                       "lenses": ["FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"]}),)
        )
    return s


def test_cube_create():
    from kg_agent import create_cube, completeness
    s = _fresh_kg_substrate()
    try:
        r = create_cube(s, "the sky is blue")
        assert "error" not in r, r
        assert r["cube_id"] == "cube/the-sky-is-blue"
        comp = completeness(s, r["cube_id"])
        assert comp["score"] == 0.0
        assert comp["complete"] is False
    finally:
        s.close()


def test_cube_fill_and_completeness():
    from kg_agent import create_cube, fill_face, completeness, LENSES
    s = _fresh_kg_substrate()
    try:
        r = create_cube(s, "test cube")
        cid = r["cube_id"]
        for i, lens in enumerate(LENSES):
            fill_face(s, cid, lens, f"content {i}")
        comp = completeness(s, cid)
        assert abs(comp["score"] - 0.80) < 1e-6, comp
        assert len(comp["filled_lenses"]) == 5
        assert comp["validated"] is False
        assert comp["complete"] is False
    finally:
        s.close()


def test_cube_validate_completes():
    from kg_agent import create_cube, fill_face, validate, completeness, LENSES
    s = _fresh_kg_substrate()
    try:
        r = create_cube(s, "test cube")
        cid = r["cube_id"]
        for i, lens in enumerate(LENSES):
            fill_face(s, cid, lens, f"content {i}")
        validate(s, cid, "james", note="looks right")
        comp = completeness(s, cid)
        assert abs(comp["score"] - 1.00) < 1e-6, comp
        assert comp["validated"] is True
        assert comp["complete"] is True
    finally:
        s.close()


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


def _complete_cube(s):
    from kg_agent import create_cube, fill_face, validate, LENSES
    cid = create_cube(s, "test cube")["cube_id"]
    for lens in LENSES:
        fill_face(s, cid, lens, f"{lens} content")
    validate(s, cid, "james")
    return cid


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


# --- rule tests ----------------------------------------------------------
def _seed_decision_substrate():
    """KG substrate with a chose-sqlite-like decision capsule."""
    from substrate import Substrate
    import json as _j
    s = Substrate(":memory:")
    s.conn.executescript((_here.parent / "schema.sql").read_text())
    with s.conn:
        for fid in ["foundation:foundation", "foundation:knowledge",
                    "foundation:cube", "foundation:lens", "foundation:cube-face",
                    "foundation:neighbour"]:
            s.conn.execute(
                "INSERT INTO capsules (id, foundation, state_json, is_meta) "
                "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,)
            )
        s.conn.execute(
            "INSERT INTO capsules (id, foundation, state_json) VALUES "
            "('chose-sqlite', 'foundation:knowledge', ?)",
            (_j.dumps({
                "kind": "decision",
                "decision": "SQLite, single file, WAL mode",
                "rationale": "One writer, many readers, no network.",
                "alternatives_considered": ["Postgres", "DuckDB"],
                "decided_by": "james",
            }),)
        )
    return s


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


def test_rule_neighbour_by_tag():
    from kg_agent import create_cube, list_proposals
    from kg_rules import run_rules
    s = _seed_decision_substrate()
    try:
        a = create_cube(s, "cube about databases")["cube_id"]
        b = create_cube(s, "another cube about databases")["cube_id"]
        # Both tagged "database"
        for cid in (a, b):
            c = s.get(cid)
            st = dict(c["state"]); st["tags"] = ["database"]
            import json as _j
            with s.conn:
                s.conn.execute(
                    "UPDATE capsules SET state_json=? WHERE id=?",
                    (_j.dumps(st), cid),
                )
        run_rules(s, a, only_rules=["neighbour_by_tag"])
        props = list_proposals(s, cube_id=a, status="pending")
        neigh = [p for p in props if p.get("proposal_type") == "neighbour"]
        assert len(neigh) == 1
        assert neigh[0]["other_cube_id"] == b
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
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
