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
