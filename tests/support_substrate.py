"""Regression suite. Run: python tests/test_substrate.py"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
for _d in ("src", "scripts", "scripts/scp", "scripts/repos", "scripts/language", "seeds"):
    sys.path.insert(0, str(ROOT / _d))
import json
import traceback

from substrate import Substrate
from signing import generate_keypair, sign, verify, canonicalise
import ed25519
from rules import evaluate_rules
from trust import compute_all, trust_from_evidence
from queries import latest


def hx(s): return bytes.fromhex(s)


def fresh_substrate():
    """In-memory DB with minimal fixtures. Never touches sc.db."""
    s = Substrate(":memory:")
    s.conn.executescript((ROOT / "schema.sql").read_text())
    with s.conn:
        s.conn.execute("""INSERT INTO capsules (id, foundation, state_json, is_meta)
            VALUES ('foundation:foundation', 'foundation:foundation', '{}', 1)""")
        for fid in ["foundation:knowledge", "foundation:observation",
                    "foundation:rule", "foundation:leighton-weight"]:
            s.conn.execute("""INSERT INTO capsules (id, foundation, state_json, is_meta)
                VALUES (?, 'foundation:foundation', '{}', 1)""", (fid,))
        s.conn.execute("""INSERT INTO capsules (id, foundation, state_json)
            VALUES ('alice', 'foundation:knowledge', '{"claim": "X"}')""")
        s.conn.execute("""INSERT INTO capsules (id, foundation, state_json)
            VALUES ('obs-1', 'foundation:observation',
                    '{"target": "alice", "score": 1.5, "source": "bob"}')""")
        s.conn.execute("""INSERT INTO links (source, type, target)
            VALUES ('obs-1', 'observes', 'alice')""")
        s.conn.execute("""INSERT INTO capsules (id, foundation, state_json)
            VALUES ('model-1', 'foundation:leighton-weight',
                    '{"formula": "N0*e^(-kt)"}')""")
    return s


def fresh_parse_fixture():
    """Substrate with foundations + lexicon + grammar for parse tests."""
    from seed_lexicon import LEXICON
    from seed_grammar import GRAMMAR
    s = Substrate(":memory:")
    s.conn.executescript((ROOT / "schema.sql").read_text())
    with s.conn:
        s.conn.execute(
            "INSERT INTO capsules (id, foundation, state_json, is_meta) "
            "VALUES ('foundation:foundation', 'foundation:foundation', '{}', 1)"
        )
        for fid in ["foundation:knowledge", "foundation:token",
                    "foundation:phrase", "foundation:sentence", "foundation:rule"]:
            s.conn.execute(
                "INSERT INTO capsules (id, foundation, state_json, is_meta) "
                "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,)
            )
    # Plurals for number tests
    LEXICON["cats"] = ("noun", {"number": "pl", "location": False})
    LEXICON["mats"] = ("noun", {"number": "pl", "location": True})
    LEXICON["a"] = ("det", {"number": "sg"})
    # SV / object test features
    LEXICON["sat"] = ("verb", {"transitive": False, "tense": "past",
                               "subject_must_be_animate": True})
    LEXICON["sits"] = ("verb", {"transitive": False, "number": "sg",
                                "subject_must_be_animate": True})
    LEXICON["chased"] = ("verb", {"transitive": True, "object_must_be_animate": True,
                                  "subject_must_be_animate": True})
    for word, (pos, features) in LEXICON.items():
        s.write({"id": f"lex/{word}", "foundation": "foundation:knowledge",
                 "state": {"kind": "lexical-entry", "text": word, "pos": pos,
                           "features": features}})
    EXTRA_RULES = [
        {"id": "grammar/np-noun",
         "state": {"condition": {"type": "sequence", "match": [
             {"foundation": "token", "state": {"pos": "noun"}}]},
                   "effect": {"foundation": "phrase", "state": {"category": "NP"}}}},
        {"id": "grammar/np-adj-noun",
         "state": {"condition": {"type": "sequence", "match": [
             {"foundation": "token", "state": {"pos": "adj"}},
             {"foundation": "token", "state": {"pos": "noun"}}]},
                   "effect": {"foundation": "phrase", "state": {"category": "NP"}}}},
        {"id": "grammar/np-noun-noun",
         "state": {"condition": {"type": "sequence", "match": [
             {"foundation": "token", "state": {"pos": "noun"}},
             {"foundation": "token", "state": {"pos": "noun"}}]},
                   "effect": {"foundation": "phrase", "state": {"category": "NP"}}}},
    ]
    for g in list(GRAMMAR) + EXTRA_RULES:
        st = dict(g["state"])
        if g["id"] == "grammar/np-det-noun":
            st = {**st, "condition": {**st["condition"], "number_agree": True}}
        if g["id"] == "grammar/s-np-vp":
            st = {**st, "condition": {**st["condition"], "subject_verb_agree": True}}
        s.write({"id": g["id"], "foundation": "foundation:rule", "state": st})
    # Test entity for query walkers
    s.write({"id": "alice", "foundation": "foundation:knowledge",
             "state": {"kind": "person", "name": "alice", "role": "test entity"}})
    return s


# --- protocol classification -------------------------------------------
def _seed_classifiers_for_test(s):
    """Add the 4 classifier capsules to a fixture."""
    import json as _j
    classifiers = [
        {"id": "classifier/01-wellbeing", "state": {
            "kind": "input-classifier", "layer": 2, "name": "wellbeing-question",
            "match_mode": "contains",
            "patterns": ["how are you", "how's it going"],
            "response_templates": ["good thanks", "not bad"]}},
        {"id": "classifier/02-greeting", "state": {
            "kind": "input-classifier", "layer": 2, "name": "greeting",
            "match_mode": "exact",
            "patterns": ["hi", "hello", "hey", "morning"],
            "response_templates": ["hi", "hello", "morning"]}},
        {"id": "classifier/03-smalltalk", "state": {
            "kind": "input-classifier", "layer": 4, "name": "smalltalk",
            "match_mode": "contains",
            "patterns": ["weather", "cold"],
            "response_templates": ["mm", "yeah"]}},
        {"id": "classifier/04-semantic", "state": {
            "kind": "input-classifier", "layer": 7, "name": "semantic",
            "match_mode": "parses", "response_templates": []}},
    ]
    for c in classifiers:
        s.write({"id": c["id"], "foundation": "foundation:knowledge", "state": c["state"]})


# --- natural language queries --------------------------------------------
def _seed_intents_for_test(s):
    from seed_intents import INTENTS
    for it in INTENTS:
        s.write({
            "id": it["id"],
            "foundation": "foundation:knowledge",
            "state": {
                "kind": "input-intent",
                "walker": it["walker"],
                "match_mode": "any_phrase",
                "phrases": it["phrases"],
                "requires_entity": it["requires_entity"],
                "description": it["description"],
            },
        })


def _absorb_fixture():
    s = Substrate(":memory:")
    s.conn.executescript((ROOT / "schema.sql").read_text())
    with s.conn:
        for fid in ("foundation:foundation", "foundation:knowledge"):
            s.conn.execute(
                "INSERT INTO capsules (id, foundation, state_json, is_meta) "
                "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
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
