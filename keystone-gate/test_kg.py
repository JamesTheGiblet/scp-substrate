"""Boundary tests for Keystone Gate.

These tests use the real DB (not :memory:) because the boundary is the whole
point — we're proving Keystone Gate can query the substrate's foundations.
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_stats import stats, count_by_foundation
from kg_router import route_list


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


def test_stats_returns_zeros_initially():
    """kg_stats runs and returns sensible zeros on an unpopulated KG."""
    st = stats()
    assert set(st.keys()) == {"cubes", "lenses", "cube_faces", "neighbours"}
    # All zero at boundary-proven-but-not-populated state
    for k, v in st.items():
        assert isinstance(v, int), f"{k} should be int, got {type(v)}"
        assert v >= 0, f"{k} should be non-negative"


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


# --- cube tests ----------------------------------------------------------
def _fresh_kg_substrate():
    """In-memory substrate with KG foundations + default-cube."""
    from substrate import Substrate
    s = Substrate(":memory:")
    s.conn.executescript(Path("schema.sql").read_text())
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
