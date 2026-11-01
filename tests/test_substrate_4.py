"""Substrate tests, part 4 of 4. Run: python tests/run.py"""
from support_substrate import *


def test_absorb_refreshes_symbol_lines():
    import shutil, tempfile
    from absorb_repo import absorb
    s = _absorb_fixture()
    tmp = Path(tempfile.mkdtemp()) / "demo"
    try:
        tmp.mkdir()
        (tmp / "a.py").write_text("def alpha():\n    pass\n")
        absorb(s, tmp, write=True)
        (tmp / "a.py").write_text("\n\n\ndef alpha():\n    pass\n")
        absorb(s, tmp, write=True)
        assert s.get("symbol/demo/a/alpha")["state"]["line"] == 4
    finally:
        s.close()
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_js_symbols():
    from absorb_repo import _extract_js_symbols
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write("import x from 'lib';\nexport function hello() {}\nexport class Thing {}\nconst world = () => {};\n")
        path = f.name
    symbols, imports = _extract_js_symbols(path)
    names = {s["name"] for s in symbols}
    assert "hello" in names
    assert "Thing" in names
    assert "world" in names
    assert "lib" in imports
    os.unlink(path)


# --- person import ------------------------------------------------------
def test_import_person():
    from substrate import Substrate
    from pathlib import Path
    from import_person import import_person
    s = Substrate(":memory:")
    s.conn.executescript((ROOT / "schema.sql").read_text())
    with s.conn:
        for fid in ["foundation:foundation", "foundation:knowledge"]:
            s.conn.execute(
                "INSERT INTO capsules (id, foundation, state_json, is_meta) "
                "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,)
            )
        s.conn.execute(
            "INSERT INTO capsules (id, foundation, state_json) "
            "VALUES ('james', 'foundation:knowledge', '{}')"
        )
        s.conn.execute(
            "INSERT INTO capsules (id, foundation, state_json) "
            "VALUES ('circadian/morning/weekday', 'foundation:knowledge', ?)",
            (json.dumps({"kind": "routine", "document_id": "circadian.morning.weekday"}),)
        )
    doc = {
        "sc_version": "1.2",
        "id": "person.test",
        "title": "Test person",
        "extends": ["person-generic"],
        "routine_links": ["circadian.morning.weekday"],
        "open_items": ["open item one"],
        "signature": {"value": None, "key_id": None, "algorithm": "Ed25519"},
    }
    result = import_person(s, doc)
    assert result["person_id"] == "person/test"
    assert result["shorthand_link"] == "james"
    assert "circadian/morning/weekday" in result["routine_links"]
    assert "person-generic" in result["extends_links"]
    # same-as links
    assert s.conn.execute(
        "SELECT 1 FROM links WHERE source='person/test' AND type='same-as' AND target='james'"
    ).fetchone()
    # follows link
    assert s.conn.execute(
        "SELECT 1 FROM links WHERE source='person/test' AND type='follows' AND target='circadian/morning/weekday'"
    ).fetchone()
    # extends link + placeholder
    assert s.get("person-generic") is not None
    assert s.conn.execute(
        "SELECT 1 FROM links WHERE source='person/test' AND type='extends' AND target='person-generic'"
    ).fetchone()
    # question
    assert s.get("person/test/open/1")


def test_import_circadian_phases():
    from substrate import Substrate
    from pathlib import Path
    from import_circadian import import_circadian
    s = Substrate(":memory:")
    s.conn.executescript((ROOT / "schema.sql").read_text())
    with s.conn:
        for fid in ["foundation:foundation", "foundation:knowledge"]:
            s.conn.execute(
                "INSERT INTO capsules (id, foundation, state_json, is_meta) "
                "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,)
            )
    doc = {
        "sc_version": "1.2", "id": "circadian.test-weekend",
        "title": "Weekend", "status": "provisional",
        "phases": {
            "p1": {"window": "Fri-Sat", "desc": "free"},
            "p2": {"window": "Sun", "desc": "split",
                   "unresolved": ["what is the work half?"]},
        },
        "signature": {"value": None, "key_id": None, "algorithm": "Ed25519"},
    }
    result = import_circadian(s, doc)
    assert result["phases_created"] == 2
    assert s.get("circadian/test-weekend/phase/p1")
    assert s.get("circadian/test-weekend/phase/p2")
    # unresolved became a question
    assert s.get("circadian/test-weekend/phase/p2/open/1")


if __name__ == "__main__":
    run_tests(globals())
