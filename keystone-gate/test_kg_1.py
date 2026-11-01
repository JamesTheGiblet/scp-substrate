"""Keystone Gate tests, part 1 of 3. Run: python tests/run.py"""
from support_kg import *


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


if __name__ == "__main__":
    run_tests(globals())
