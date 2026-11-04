"""Substrate tests, part 2 of 4. Run: python tests/run.py"""
from support_substrate import *


# --- weighted choice -----------------------------------------------------
def test_weighted_choice_prefers_common():
    """Corpus learning biases generation toward frequent words."""
    from store.substrate import Substrate
    from seed_corpus import CORPUS_SENTENCES as CORPUS
    from learn_frequencies import main as learn  # not used; do it inline
    from symlm.generate import generate_sentence
    from symlm.parse import parse_sentence, cleanup_session

    s = fresh_parse_fixture()

    # Learn frequencies inline (fresh_parse_fixture has empty trust)
    from collections import Counter
    counts = Counter()
    for text in CORPUS:
        r = parse_sentence(s, text)
        if "error" in r or not r["sentence"]:
            continue
        stack = [r["sentence"]]; seen = set()
        while stack:
            cid = stack.pop()
            if cid in seen: continue
            seen.add(cid)
            c = s.get(cid)
            if not c: continue
            if c["foundation"] == "foundation:token":
                counts[c["state"]["text"]] += 1
            for l in s.links_from(cid):
                if l["type"] == "has-child": stack.append(l["target"])
        cleanup_session(s, r["session"])

    import json
    for word, count in counts.items():
        s.write({
            "id": f"trust/freq/{word}",
            "foundation": "foundation:leighton-weight",
            "state": {"n0": count, "k": 0, "word": word},
        })

    # Generate 40 sentences and count how often "the" (frequent) appears
    # vs "a" (less frequent) in the determiner slot.
    the_count = 0
    a_count = 0
    for seed in range(40):
        r = generate_sentence(s, seed=seed)
        if "error" in r: continue
        toks = r["tokens"]
        if toks and toks[0] == "the": the_count += 1
        if toks and toks[0] == "a": a_count += 1
        cleanup_session(s, r["session"])

    assert the_count > a_count, f"expected 'the' > 'a', got {the_count} vs {a_count}"


# --- semantic filtering -------------------------------------------------
def test_semantic_blocks_animal_location():
    """'on'/'in' require a location; animals are not locations."""
    from symlm.generate import generate_sentence
    from symlm.parse import cleanup_session
    s = fresh_parse_fixture()

    violations = 0
    for seed in range(40):
        r = generate_sentence(s, seed=seed)
        if "error" in r:
            continue
        toks = r["tokens"]
        for i, t in enumerate(toks):
            if t in ("on", "in"):
                for j in range(i + 1, len(toks)):
                    if toks[j] in ("cat", "dog"):
                        violations += 1
                        break
        cleanup_session(s, r["session"])
    assert violations == 0, f"{violations} sentences with 'on/in <animal>'"


def test_semantic_allows_object_location():
    """'on the mat' should still generate — mat is a location."""
    from symlm.generate import generate_sentence
    from symlm.parse import cleanup_session
    s = fresh_parse_fixture()

    found = False
    for seed in range(60):
        r = generate_sentence(s, seed=seed)
        if "error" in r:
            continue
        if "mat" in r["tokens"] and any(t in ("on", "in") for t in r["tokens"]):
            found = True
            cleanup_session(s, r["session"])
            break
        cleanup_session(s, r["session"])
    assert found, "never generated 'on ... mat' in 60 seeds"


# --- gap analysis --------------------------------------------------------
def test_gap_analysis_raw_span():
    """'the big red cat sat' -> unreduced tokens at [0-3] (det adj adj noun)."""
    from symlm.analysis import find_gap_spans
    s = fresh_parse_fixture()
    s.write({"id": "lex/red", "foundation": "foundation:knowledge",
             "state": {"kind": "lexical-entry", "text": "red", "pos": "adj",
                       "features": {}}})
    r = find_gap_spans(s, "the big red cat sat")
    assert not r.get("ok"), r
    assert r["gaps"], r
    first_gap = r["gaps"][0]
    a, b, seq = first_gap
    # With np-adj-noun rule, "red cat" reduces to NP[2-3],
    # leaving "the big" as the unreduced gap.
    assert (a, b) == (0, 1), f"expected gap [0-1], got [{a}-{b}]"
    assert seq == ["det", "adj"], seq


def test_gap_analysis_composition_gap():
    """'the cat sat the dog' -> sat is intransitive, can't take an object."""
    from symlm.analysis import find_gap_spans
    s = fresh_parse_fixture()
    r = find_gap_spans(s, "the cat sat the dog")
    assert not r.get("ok"), r
    assert not r["gaps"], f"expected no raw gap, got {r['gaps']}"
    assert len(r["maximal"]) >= 2, r["maximal"]


def test_gap_analysis_ok():
    """A parseable sentence returns ok=True."""
    from symlm.analysis import find_gap_spans
    s = fresh_parse_fixture()
    r = find_gap_spans(s, "the cat sat")
    assert r.get("ok") is True, r


# --- transitivity --------------------------------------------------------
def test_parse_transitive():
    """'the cat chased the dog' parses via VP -> verb(transitive) NP."""
    from symlm.parse import parse_sentence
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat chased the dog")
    assert "error" not in r, r
    assert r["sentence"] is not None, r


def test_parse_transitive_needs_object():
    """'the cat chased' -> transitive verb without object doesn't produce S."""
    from symlm.parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat chased")
    assert "error" not in r, r
    assert r["sentence"] is None, f"expected no S, got {r['sentence']}"
    cleanup_session(s, r["session"])


def test_parse_intransitive_rejects_object():
    """'the cat sat the dog' -> sat is intransitive, no VP -> verb NP."""
    from symlm.parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat sat the dog")
    assert "error" not in r, r
    assert r["sentence"] is None, f"expected no full S, got {r['sentence']}"
    cleanup_session(s, r["session"])


# --- number agreement ----------------------------------------------------
def test_number_agreement():
    """'a cats' must fail; 'the cats' must parse."""
    from symlm.parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    for text, expect_ok in [
        ("a cat sat", True),
        ("a cats sat", False),
        ("the cats sat", True),
        ("the cat sat", True),
    ]:
        r = parse_sentence(s, text)
        got = r.get("sentence") is not None
        assert got == expect_ok, f"{text!r}: expected {expect_ok}, got {got}"
        if r.get("session"):
            cleanup_session(s, r["session"])


# --- feedback ------------------------------------------------------------
def test_feedback_confirm():
    """Confirming a session raises trust for its words and rules."""
    from symlm.parse import parse_sentence, cleanup_session
    from symlm.feedback import apply_feedback
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat sat")
    sess = r["session"]

    before = s.conn.execute("SELECT COUNT(*) FROM capsules WHERE id LIKE 'trust/%'").fetchone()[0]
    result = apply_feedback(s, sess, positive=True)
    after = s.conn.execute("SELECT COUNT(*) FROM capsules WHERE id LIKE 'trust/%'").fetchone()[0]
    assert after > before, f"no trust written: {result}"

    row = s.conn.execute("""
        SELECT json_extract(state_json, '$.n0') AS n0 FROM capsules
        WHERE foundation = 'foundation:leighton-weight'
          AND json_extract(state_json, '$.word') = 'the'
    """).fetchone()
    assert row and row["n0"] >= 1
    cleanup_session(s, sess)


def test_feedback_reject_lowers():
    """Confirm twice, reject once → trust net +1."""
    from symlm.parse import parse_sentence, cleanup_session
    from symlm.feedback import apply_feedback
    s = fresh_parse_fixture()

    for _ in range(2):
        r = parse_sentence(s, "the cat sat")
        apply_feedback(s, r["session"], positive=True)
        cleanup_session(s, r["session"])

    row = s.conn.execute("""
        SELECT json_extract(state_json, '$.n0') AS n0 FROM capsules
        WHERE foundation = 'foundation:leighton-weight'
          AND json_extract(state_json, '$.word') = 'the'
    """).fetchone()
    confirmed = row["n0"]
    assert confirmed >= 2

    r = parse_sentence(s, "the cat sat")
    apply_feedback(s, r["session"], positive=False)
    cleanup_session(s, r["session"])

    row = s.conn.execute("""
        SELECT json_extract(state_json, '$.n0') AS n0 FROM capsules
        WHERE foundation = 'foundation:leighton-weight'
          AND json_extract(state_json, '$.word') = 'the'
    """).fetchone()
    assert row["n0"] == confirmed - 1, f"expected {confirmed - 1}, got {row['n0']}"


# --- SV agreement & object semantics ------------------------------------
def test_sv_agreement():
    """Plural subject with 3sg verb must fail; past tense passes (no number)."""
    from symlm.parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    cases = [
        ("the cats sits", False),   # pl subject, sg verb → fail
        ("the cats sat", True),     # pl subject, past verb (no number) → pass
        ("the cat sits", True),     # sg subject, sg verb → pass
    ]
    for text, expect_ok in cases:
        r = parse_sentence(s, text)
        got = r.get("sentence") is not None
        assert got == expect_ok, f"{text!r}: expected {expect_ok}, got {got}"
        if r.get("session"):
            cleanup_session(s, r["session"])


def test_object_must_be_animate():
    """'chased' requires an animate object; mat fails, dog passes."""
    from symlm.parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    cases = [
        ("the cat chased the mat", False),   # mat not animate → fail
        ("the cat chased the dog", True),    # dog animate → pass
    ]
    for text, expect_ok in cases:
        r = parse_sentence(s, text)
        got = r.get("sentence") is not None
        assert got == expect_ok, f"{text!r}: expected {expect_ok}, got {got}"
        if r.get("session"):
            cleanup_session(s, r["session"])


def test_classify_greeting():
    from symlm.protocol import classify
    s = fresh_parse_fixture()
    _seed_classifiers_for_test(s)
    r = classify(s, "hi")
    assert r["layer"] == 2 and r["kind"] == "greeting", r


def test_classify_wellbeing():
    from symlm.protocol import classify
    s = fresh_parse_fixture()
    _seed_classifiers_for_test(s)
    r = classify(s, "how are you")
    assert r["layer"] == 2 and r["kind"] == "wellbeing-question", r


def test_classify_semantic():
    from symlm.protocol import classify
    s = fresh_parse_fixture()
    _seed_classifiers_for_test(s)
    r = classify(s, "the cat sat")
    assert r["layer"] == 7 and r["kind"] == "semantic", r


def test_classify_unknown():
    from symlm.protocol import classify
    s = fresh_parse_fixture()
    _seed_classifiers_for_test(s)
    r = classify(s, "flibbertigibbet")
    assert r["layer"] == 0 and r["kind"] == "unknown", r


def test_respond_ack_mode():
    """'hi' returns a template, not a word dump."""
    from symlm.talk import respond
    s = fresh_parse_fixture()
    _seed_classifiers_for_test(s)
    out = respond(s, "hi", 1, "sess-t1")
    assert "Words I know" not in out, out
    assert len(out) < 40, out


def test_respond_layer7_concise():
    """'the cat sat' produces a generated sentence, no word dump."""
    from symlm.talk import respond
    s = fresh_parse_fixture()
    _seed_classifiers_for_test(s)
    out = respond(s, "the cat sat", 1, "sess-t2")
    assert "Words I know" not in out, out
    assert "So:" in out, out


# --- expansion ----------------------------------------------------------
def test_endswith_classifier():
    from symlm.protocol import classify
    s = fresh_parse_fixture()
    # Seed a minimal endswith classifier
    s.write({"id": "classifier/09-question-mark",
             "foundation": "foundation:knowledge",
             "state": {"kind": "input-classifier", "layer": 3, "name": "question-mark",
                       "match_mode": "endswith", "patterns": ["?"],
                       "response_templates": ["dunno"]}})
    r = classify(s, "what time is it?")
    assert r["layer"] == 3 and r["kind"] == "question-mark", r


def test_alias_lookup():
    from store.substrate import Substrate
    from symlm.parse import _lookup_entry
    s = fresh_parse_fixture()
    s.write({"id": "alias/an", "foundation": "foundation:knowledge",
             "state": {"kind": "alias", "alias_for": "a", "text": "an",
                       "pos": "det", "features": {}}})
    e = _lookup_entry(s, "an")
    assert e and e["pos"] == "det", e


def test_typo_lookup():
    from store.substrate import Substrate
    from symlm.parse import _lookup_entry
    s = fresh_parse_fixture()
    s.write({"id": "typo/teh", "foundation": "foundation:knowledge",
             "state": {"kind": "typo", "alias_for": "the", "text": "teh",
                       "pos": "det", "features": {}}})
    e = _lookup_entry(s, "teh")
    assert e and e["pos"] == "det", e


if __name__ == "__main__":
    run_tests(globals())
