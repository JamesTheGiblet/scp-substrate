"""Substrate tests, part 3 of 4. Run: python tests/run.py"""
from support_substrate import *


def test_subject_must_be_animate():
    from parse import parse_sentence, cleanup_session
    import json
    s = fresh_parse_fixture()
    # Tag sat
    c = s.get("lex/sat")
    f = dict(c["state"].get("features", {})); f["subject_must_be_animate"] = True
    st = dict(c["state"]); st["features"] = f
    with s.conn:
        s.conn.execute("UPDATE capsules SET state_json=? WHERE id='lex/sat'",
                       (json.dumps(st),))
    # S rule needs subject_verb_agree to fire the check
    c = s.get("grammar/s-np-vp")
    ns = dict(c["state"]); ns["condition"] = {**ns["condition"], "subject_verb_agree": True}
    with s.conn:
        s.conn.execute("UPDATE capsules SET state_json=? WHERE id='grammar/s-np-vp'",
                       (json.dumps(ns),))

    cases = [
        ("the cat sat", True),
        ("the mat sat", False),
    ]
    for text, expect_ok in cases:
        r = parse_sentence(s, text)
        got = r.get("sentence") is not None
        assert got == expect_ok, f"{text!r}: expected {expect_ok}, got {got}"
        if r.get("session"):
            cleanup_session(s, r["session"])


# --- wh-startswith classifier --------------------------------------------
def test_wh_startswith_classifier():
    from protocol import classify
    s = fresh_parse_fixture()
    s.write({
        "id": "classifier/11-wh-question",
        "foundation": "foundation:knowledge",
        "state": {"kind": "input-classifier", "layer": 3, "name": "wh-question",
                  "match_mode": "startswith",
                  "patterns": ["what", "who", "where", "when", "why", "how"],
                  "response_templates": ["dunno"]},
    })
    for text in ["what time is it", "who is that", "where are we", "why not"]:
        r = classify(s, text)
        assert r["layer"] == 3, f"{text!r}: expected layer 3, got {r}"


# --- expanded NP grammar -------------------------------------------------
def test_np_bare_noun():
    """'cat sat' parses via NP -> noun (bare)."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "cat sat")
    assert r.get("sentence"), r
    cleanup_session(s, r["session"])


def test_np_adj_noun():
    """'big cat sat' parses via NP -> adj noun."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "big cat sat")
    assert r.get("sentence"), r
    cleanup_session(s, r["session"])


def test_np_noun_noun():
    """'house cat sat' parses via NP -> noun noun (compound)."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "house cat sat")
    assert r.get("sentence"), r
    cleanup_session(s, r["session"])


def test_permissive_animacy_missing():
    """Missing animacy feature passes the object check (permissive)."""
    from parse import parse_sentence, cleanup_session
    import json
    s = fresh_parse_fixture()
    # Add a bare noun with no features
    s.write({"id": "lex/substrate", "foundation": "foundation:knowledge",
             "state": {"kind": "lexical-entry", "text": "substrate",
                       "pos": "noun", "features": {}}})
    r = parse_sentence(s, "the cat chased substrate")
    assert r.get("sentence"), r
    cleanup_session(s, r["session"])


# --- animacy feature tags ------------------------------------------------
def test_abstract_object_blocked():
    """Tagged-abstract noun as object of 'chased' fails."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    s.write({"id": "lex/substrate", "foundation": "foundation:knowledge",
             "state": {"kind": "lexical-entry", "text": "substrate",
                       "pos": "noun", "features": {"animacy": "abstract"}}})
    r = parse_sentence(s, "the cat chased substrate")
    assert not r.get("sentence"), r
    cleanup_session(s, r["session"])


def test_object_subject_blocked():
    """Tagged-object noun as subject of 'sat' fails."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    s.write({"id": "lex/capsule", "foundation": "foundation:knowledge",
             "state": {"kind": "lexical-entry", "text": "capsule",
                       "pos": "noun", "features": {"animacy": "object"}}})
    r = parse_sentence(s, "capsule sat")
    assert not r.get("sentence"), r
    cleanup_session(s, r["session"])


def test_animal_subject_passes():
    """Tagged-animal noun as subject of 'sat' passes."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    # 'cat' already has animacy: animal from fixture
    r = parse_sentence(s, "cat sat")
    assert r.get("sentence"), r
    cleanup_session(s, r["session"])


def test_intent_why_trusted():
    from ask import classify_intent
    s = fresh_parse_fixture()
    _seed_intents_for_test(s)
    r = classify_intent(s, "why is scp-claim trusted")
    assert r and r["walker"] == "why_trusted", r


def test_intent_what_decided():
    from ask import classify_intent
    s = fresh_parse_fixture()
    _seed_intents_for_test(s)
    r = classify_intent(s, "what did i decide about sqlite")
    assert r and r["walker"] == "what_decided", r


def test_intent_no_match():
    from ask import classify_intent
    s = fresh_parse_fixture()
    _seed_intents_for_test(s)
    r = classify_intent(s, "the cat sat")
    assert r is None, r


def test_extract_entity_direct_id():
    from ask import extract_entity
    s = fresh_parse_fixture()
    entity = extract_entity(s, "why is alice trusted", {"walker": "why_trusted"})
    assert entity == "alice", entity


def test_ask_returns_result():
    from ask import answer_question
    s = fresh_parse_fixture()
    _seed_intents_for_test(s)
    # 'who is alice' → what_is walker
    r = answer_question(s, "who is alice")
    assert r is not None
    assert "alice" in r.get("summary", "").lower(), r


# --- symbol extraction ---------------------------------------------------
def test_python_symbols():
    from absorb_repo import _extract_python_symbols
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("import json\nfrom pathlib import Path\n\ndef foo(x):\n    return x\n\nclass Bar:\n    def baz(self):\n        pass\n")
        path = f.name
    symbols, imports = _extract_python_symbols(path)
    names = {s["name"] for s in symbols}
    assert "foo" in names
    assert "Bar" in names
    assert "Bar.baz" in names
    assert "json" in imports
    assert "pathlib" in imports
    os.unlink(path)


def test_keygen_help_writes_no_key():
    import os, shutil, subprocess, tempfile
    home = Path(tempfile.mkdtemp())
    try:
        env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "keygen.py"), "--help"],
                           capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        assert list(home.iterdir()) == [], list(home.iterdir())
    finally:
        shutil.rmtree(home, ignore_errors=True)


def test_keygen_writes_named_key():
    import shutil, tempfile
    import keygen
    tmp = Path(tempfile.mkdtemp())
    saved_dir, saved_argv = keygen.KEYS_DIR, sys.argv
    try:
        keygen.KEYS_DIR = tmp / "a" / "b" / "keys"
        keygen.KEYS_DIR.mkdir(parents=True)
        sys.argv = ["keygen.py", "demo"]
        keygen.main()
        assert json.loads((keygen.KEYS_DIR / "demo.json").read_text())["did_key"]
    finally:
        keygen.KEYS_DIR, sys.argv = saved_dir, saved_argv
        shutil.rmtree(tmp, ignore_errors=True)


def test_absorb_updates_are_event_logged():
    import shutil, tempfile
    from absorb_repo import absorb
    s = _absorb_fixture()
    tmp = Path(tempfile.mkdtemp()) / "demo"
    try:
        tmp.mkdir()
        (tmp / "a.py").write_text("import os\n")
        absorb(s, tmp, write=True)
        (tmp / "a.py").write_text("import sys\n")
        absorb(s, tmp, write=True)
        logged = dict(s.conn.execute(
            "SELECT capsule_id, COUNT(*) FROM events "
            "WHERE event_type='capsule.written' GROUP BY capsule_id"
        ).fetchall())
        assert logged["repo/demo"] == 2, logged
        # created, imports added, then changed + imports changed
        assert logged["file/demo/a.py"] == 4, logged
    finally:
        s.close()
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_import_scp_document():
    from import_scp import import_scp
    s = fresh_substrate()
    try:
        s.write({"id": "subject", "foundation": "foundation:knowledge", "state": {}})
        doc = {
            "scp_id": "forge/doc-v1",
            "scp_version": "1.2",
            "declaration": {"entity": {"capsule": "subject"}},
            "inherits": ["forge/parent"],
            "signature": {"value": "abc", "key_id": "did:key:z", "algorithm": "Ed25519"},
        }
        r = import_scp(s, doc, source_path="doc.json")
        assert r["signed"] is True, r
        assert r["declares"] == "subject", r
        assert r["inherits_created"] == ["forge/parent"], r
        types = {(l["type"], l["target"]) for l in s.get("forge/doc-v1")["links"]}
        assert ("inherits", "forge/parent") in types, types
        assert ("declares", "subject") in types, types
    finally:
        s.close()


def test_import_scp_help_exits_cleanly():
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "import_scp.py"), "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "usage" in r.stdout, r


def test_why_walks_back_through_rule_and_model():
    from why import why_trusted
    s = fresh_substrate()
    try:
        s.write({"id": "trust-a", "foundation": "foundation:leighton-weight",
                 "state": {"n0": 1.0, "k": 0, "age_days": 0}})
        s.link("trust-a", "about", "alice")
        s.write({"id": "trusted-rule", "foundation": "foundation:rule",
                 "state": {"condition": {"type": "trust_above", "threshold": 0.5},
                           "effect": {"relationship": "trusted", "derive_from": "about"}}})
        compute_all(s)
        evaluate_rules(s)
        chain = why_trusted(s, "trust-a")
        assert chain["derived_link"]["target"] == "alice", chain
        assert abs(chain["score"]["score"] - 1.0) < 1e-6, chain
        assert chain["model"]["id"] == "model-1", chain
        assert chain["about"] == "alice", chain
    finally:
        s.close()


def test_why_reports_untrusted():
    from why import why_trusted
    s = fresh_substrate()
    try:
        assert why_trusted(s, "alice") == {"claim": "alice", "trusted": False}
    finally:
        s.close()


def test_explain_narrates_state_and_links():
    from explain import explain
    s = fresh_substrate()
    try:
        s.write({"id": "bob", "foundation": "foundation:knowledge",
                 "state": {"claim": "Y"}})
        s.link("bob", "uses", "alice")
        text = explain(s, "bob")
        assert 'claim: "Y"' in text, text
        assert "uses" in text and "alice" in text, text
    finally:
        s.close()


def test_scps_cli_runs():
    """The CLI starts and lists its commands."""
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scps"), "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for cmd in ("ask", "explain", "trust", "stats"):
        assert cmd in r.stdout, cmd


def test_absorb_uses_forward_slashes_and_prunes_renames():
    import shutil, tempfile
    from absorb_repo import absorb
    s = _absorb_fixture()
    tmp = Path(tempfile.mkdtemp()) / "demo"
    try:
        (tmp / "sub").mkdir(parents=True)
        (tmp / "sub" / "a.py").write_text("def alpha():\n    pass\n")
        absorb(s, tmp, write=True)
        assert s.get("file/demo/sub/a.py")
        assert s.get("symbol/demo/sub_a/alpha")["state"]["file"] == "sub/a.py"

        # Move the file: the old capsules must go, the new ones must exist
        (tmp / "sub" / "a.py").rename(tmp / "b.py")
        r = absorb(s, tmp, write=True, prune_stale=True)
        assert r["pruned"] == 2, r
        assert s.get("file/demo/sub/a.py") is None
        assert s.get("symbol/demo/sub_a/alpha") is None
        assert s.get("symbol/demo/b/alpha")["state"]["file"] == "b.py"
        assert s.conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='capsule.deleted'"
        ).fetchone()[0] == 2
        assert s.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        s.close()
        shutil.rmtree(tmp.parent, ignore_errors=True)


if __name__ == "__main__":
    run_tests(globals())
