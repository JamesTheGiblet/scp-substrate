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

# keystone-gate, one folder up. Tests import its modules and its seeds
_here = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_here.parent / "src"), str(_here), str(_here.parent / "seeds" / "claims"),
                 str(_here.parent / "seeds" / "claims" / "before-pivot")]

from store import substrate
from store.substrate import Substrate
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
    from kg_llm import ask_llm
    s = Substrate()
    try:
        return ask_llm(s, question, client=client)
    finally:
        s.close()


GOOD_CLAIM = {"text": "James is a builder.", "evidence": "is a person — builder"}


# --- cube tests ----------------------------------------------------------
def _fresh_kg_substrate():
    """In-memory substrate with KG foundations + default-cube."""
    from store.substrate import Substrate
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


def _complete_cube(s):
    from kg_agent import create_cube, fill_face, validate, LENSES
    cid = create_cube(s, "test cube")["cube_id"]
    for lens in LENSES:
        fill_face(s, cid, lens, f"{lens} content")
    validate(s, cid, "james")
    return cid


def _answers(*replies):
    queue = iter(replies)
    return lambda prompt: next(queue)


def _draft_cube(s):
    from kg_agent import create_cube, propose_face
    cid = create_cube(s, "test cube")["cube_id"]
    for lens in ("FACT", "COUNTER", "FICTION", "CONTEXT"):
        propose_face(s, cid, lens, f"{lens} draft", proposed_by="draft")
    return cid


# --- rule tests ----------------------------------------------------------
def _seed_decision_substrate():
    """KG substrate with a chose-sqlite-like decision capsule."""
    from store.substrate import Substrate
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


def run_tests(namespace):
    """Run every test_* in a module's namespace and exit with the result."""
    tests = [v for k, v in sorted(namespace.items())
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


__all__ = [n for n in globals() if not n.startswith("__")]
