"""Regression suite. Run: python test_substrate.py"""
import json
import sys
import traceback
from pathlib import Path

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
    s.conn.executescript(Path("schema.sql").read_text())
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
    s.conn.executescript(Path("schema.sql").read_text())
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
    LEXICON["sits"] = ("verb", {"transitive": False, "number": "sg"})
    LEXICON["chased"] = ("verb", {"transitive": True, "object_must_be_animate": True})
    for word, (pos, features) in LEXICON.items():
        s.write({"id": f"lex/{word}", "foundation": "foundation:knowledge",
                 "state": {"kind": "lexical-entry", "text": word, "pos": pos,
                           "features": features}})
    for g in GRAMMAR:
        st = dict(g["state"])
        if g["id"] == "grammar/np-det-noun":
            st = {**st, "condition": {**st["condition"], "number_agree": True}}
        if g["id"] == "grammar/s-np-vp":
            st = {**st, "condition": {**st["condition"], "subject_verb_agree": True}}
        s.write({"id": g["id"], "foundation": "foundation:rule", "state": st})
    return s


# --- crypto ---------------------------------------------------------------
def test_ed25519_rfc_vector_1():
    sk = hx("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pk = hx("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    assert ed25519.publickey(sk) == pk
    sig = ed25519.sign(b"", sk, pk)
    expected = hx("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e0652249015"
                  "55fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert sig == expected
    ed25519.checkvalid(expected, b"", pk)


def test_sign_verify_roundtrip():
    kp = generate_keypair()
    signed = sign({"a": 1, "b": [2, 3]}, kp["private_b64"])
    r = verify(signed)
    assert r["signed"] and r["valid"]


def test_tamper_detection():
    kp = generate_keypair()
    signed = sign({"n": 42}, kp["private_b64"])
    tampered = json.loads(json.dumps(signed))
    tampered["n"] = 43
    assert verify(tampered)["valid"] is False


def test_canonicalise_deterministic():
    a = {"b": 2, "a": 1, "signature": {"value": "xxx", "key_id": "k"}}
    b = {"signature": {"key_id": "k", "value": "yyy"}, "a": 1, "b": 2}
    assert canonicalise(a) == canonicalise(b)


# --- substrate ------------------------------------------------------------
def test_get():
    c = fresh_substrate().get("alice")
    assert c["id"] == "alice"
    assert c["state"]["claim"] == "X"


def test_write_and_link():
    s = fresh_substrate()
    s.write({"id": "bob", "foundation": "foundation:knowledge",
             "state": {"claim": "Y"}})
    s.link("bob", "supports", "alice")
    assert s.get("bob")
    assert any(l["type"] == "supports" for l in s.links_from("bob"))


def test_foundation_protection():
    try:
        fresh_substrate().write({"id": "foundation:evil",
                                 "foundation": "foundation:knowledge",
                                 "state": {}})
        assert False, "should have raised"
    except ValueError:
        pass


# --- rules ----------------------------------------------------------------
def test_rules_idempotent():
    s = fresh_substrate()
    s.write({"id": "bob", "foundation": "foundation:knowledge", "state": {}})
    s.write({"id": "rule-1", "foundation": "foundation:rule",
             "state": {"condition": {"source": "bob", "target": "alice"},
                       "effect": {"relationship": "supports"}}})
    f1, _ = evaluate_rules(s)
    f2, _ = evaluate_rules(s)
    assert len(f1) >= 1
    assert len(f2) == 0


def test_rules_malformed_warns():
    s = fresh_substrate()
    s.write({"id": "bad-rule", "foundation": "foundation:rule", "state": {}})
    _, warnings = evaluate_rules(s)
    assert any("bad-rule" in w for w in warnings)


# --- trust ----------------------------------------------------------------
def test_trust_parameter():
    s = fresh_substrate()
    s.write({"id": "trust-1", "foundation": "foundation:leighton-weight",
             "state": {"n0": 1.0, "k": 0.01, "age_days": 0}})
    result = compute_all(s)
    assert result["computed"] == 1
    row = s.conn.execute(
        "SELECT score FROM trust_scores WHERE capsule_id='trust-1'"
    ).fetchone()
    assert abs(row["score"] - 1.0) < 0.001


def test_trust_from_evidence():
    s = fresh_substrate()
    s.write({"id": "trust-1", "foundation": "foundation:leighton-weight",
             "state": {"n0": 1.0, "k": 0.01}})
    s.link("trust-1", "about", "alice")
    result = trust_from_evidence(s, "trust-1")
    assert abs(result["score"] - 1.5) < 0.01
    assert any(e["id"] == "obs-1" for e in result["evidence"])


# --- versioning -----------------------------------------------------------
def test_supersede():
    s = fresh_substrate()
    s.write({"id": "v1", "foundation": "foundation:knowledge",
             "state": {"claim": "old"}})
    s.supersede("v1", "v2", {"claim": "new"})
    assert s.get("v2")
    assert s.get("v1")["state"].get("superseded_by") == "v2"
    assert latest(s, "v1") == "v2"
    assert latest(s, "v2") == "v2"


def test_supersede_rejects_missing_old():
    try:
        fresh_substrate().supersede("nope", "nope-v2", {})
        assert False, "should have raised"
    except ValueError:
        pass


# --- runner ---------------------------------------------------------------


# --- fusion --------------------------------------------------------------
def test_sigmoid():
    from trust import sigmoid
    assert abs(sigmoid(0) - 0.5) < 1e-9
    assert abs(sigmoid(2) - 0.880797) < 1e-4
    assert abs(sigmoid(-2) - 0.119203) < 1e-4


def test_fuse_no_evidence():
    from trust import fuse
    # Evidence = 0 → L = 0.5 → posterior = prior
    assert abs(fuse(0.7, 0) - 0.7) < 1e-6
    assert abs(fuse(0.2, 0) - 0.2) < 1e-6


def test_fuse_mid_prior_strong_evidence():
    from trust import fuse
    # prior 0.5 (uncertain), evidence +2 → posterior ≈ 0.88
    assert abs(fuse(0.5, 2) - 0.88) < 0.01
    # prior 0.5, evidence -2 → posterior ≈ 0.12
    assert abs(fuse(0.5, -2) - 0.12) < 0.01


def test_fuse_disagreement_moves():
    from trust import fuse
    # Prior confident-positive (0.9), evidence strong-negative (-2)
    # Posterior should move toward 0.5 but not below
    p = fuse(0.9, -2)
    assert 0.5 < p < 0.9


def test_fuse_clamping():
    from trust import fuse
    # prior=1, evidence=-10 → posterior > 0 (clamping prevents freeze)
    p = fuse(1.0, -10)
    assert 0.0 < p < 1.0
    # prior=0, evidence=+10 → posterior > 0
    p2 = fuse(0.0, 10)
    assert 0.0 < p2 < 1.0


def test_fused_trust_integration():
    from trust import fused_trust, compute_all
    s = fresh_substrate()
    s.write({"id": "trust-1", "foundation": "foundation:leighton-weight",
             "state": {"n0": 0.8, "k": 0.01}})
    s.link("trust-1", "about", "alice")
    # trust_now reads trust_scores, so materialize the parameter score first
    compute_all(s)
    r = fused_trust(s, "trust-1")
    assert "error" not in r
    # trust_now decays since materialization, so prior will be slightly
    # below 0.8 by the time fused_trust reads it. Check the ballpark.
    assert abs(r["prior"] - 0.8) < 0.001, f"prior was {r['prior']}, expected ≈ 0.8"
    assert r["evidence_score"] > 0
    assert 0.0 < r["posterior"] < 1.0
    assert r["source"] == "both"


def test_kind_and_age_rule():
    from datetime import datetime, timezone, timedelta
    s = fresh_substrate()
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    s.write({"id": "old-question", "foundation": "foundation:knowledge", "state": {
        "kind": "question",
        "question": "Does this test work?",
        "raised": old_date,
        "status": "open",
    }})
    s.write({"id": "holder", "foundation": "foundation:knowledge", "state": {}})
    s.link("holder", "open-question", "old-question")
    s.write({"id": "stale-rule", "foundation": "foundation:rule", "state": {
        "condition": {"type": "kind_and_age", "kind": "question",
                      "min_age_days": 7, "age_field": "raised",
                      "via_link": "open-question"},
        "effect": {"relationship": "stale-question",
                   "derive_from": "open-question"},
    }})
    fired, warnings = evaluate_rules(s)
    assert len(fired) == 1, f"expected 1 fire, got {len(fired)}; warnings={warnings}"
    assert fired[0] == ("stale-rule", "holder", "stale-question", "old-question")
    f2, _ = evaluate_rules(s)
    assert len(f2) == 0, "rule should be idempotent"


def test_kind_and_age_skips_young_question():
    from datetime import datetime, timezone
    s = fresh_substrate()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s.write({"id": "new-question", "foundation": "foundation:knowledge", "state": {
        "kind": "question", "question": "Recent?", "raised": today, "status": "open",
    }})
    s.write({"id": "holder", "foundation": "foundation:knowledge", "state": {}})
    s.link("holder", "open-question", "new-question")
    s.write({"id": "stale-rule", "foundation": "foundation:rule", "state": {
        "condition": {"type": "kind_and_age", "kind": "question",
                      "min_age_days": 7, "age_field": "raised",
                      "via_link": "open-question"},
        "effect": {"relationship": "stale-question", "derive_from": "open-question"},
    }})
    fired, _ = evaluate_rules(s)
    assert len(fired) == 0


# --- parse ---------------------------------------------------------------
def test_parse_simple():
    from parse import parse_sentence
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat sat")
    assert "error" not in r, r
    assert r["sentence"] is not None
    assert r["n_tokens"] == 3


def test_parse_pp():
    from parse import parse_sentence
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat sat on the mat")
    assert "error" not in r, r
    assert r["sentence"] is not None
    assert r["n_tokens"] == 6


def test_parse_adj():
    from parse import parse_sentence
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the big cat sat")
    assert "error" not in r, r
    assert r["sentence"] is not None


def test_parse_unknown_word():
    from parse import parse_sentence
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the zzz sat")
    assert "error" in r
    assert "zzz" in r["error"]


def test_parse_cleanup():
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat sat")
    sess = r["session"]
    before = s.conn.execute(
        "SELECT COUNT(*) FROM capsules WHERE id LIKE ?",
        (f"parse/{sess}/%",)
    ).fetchone()[0]
    assert before > 0
    cleanup_session(s, sess)
    after = s.conn.execute(
        "SELECT COUNT(*) FROM capsules WHERE id LIKE ?",
        (f"parse/{sess}/%",)
    ).fetchone()[0]
    assert after == 0


# --- generate ------------------------------------------------------------
def test_generate_simple():
    from generate import generate_sentence
    s = fresh_parse_fixture()
    r = generate_sentence(s, seed=42)
    assert "error" not in r, r
    assert len(r["tokens"]) >= 2
    assert r["root"]


def test_generate_deterministic():
    from generate import generate_sentence
    s = fresh_parse_fixture()
    a = generate_sentence(s, seed=123)
    b = generate_sentence(s, seed=123)
    assert a["text"] == b["text"]


def test_generate_then_parse():
    from generate import generate_sentence
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = generate_sentence(s, seed=7)
    assert "error" not in r, r
    text = r["text"]
    cleanup_session(s, r["session"])
    p = parse_sentence(s, text)
    assert "error" not in p, f"generated {text!r} doesn't re-parse: {p}"
    assert p["sentence"] is not None, f"generated {text!r} parse has no S"


# --- weighted choice -----------------------------------------------------
def test_weighted_choice_prefers_common():
    """Corpus learning biases generation toward frequent words."""
    from substrate import Substrate
    from seed_corpus import CORPUS_SENTENCES as CORPUS
    from learn_frequencies import main as learn  # not used; do it inline
    from generate import generate_sentence
    from parse import parse_sentence, cleanup_session

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
    from generate import generate_sentence
    from parse import cleanup_session
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
    from generate import generate_sentence
    from parse import cleanup_session
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
    from analysis import find_gap_spans
    s = fresh_parse_fixture()
    s.write({"id": "lex/red", "foundation": "foundation:knowledge",
             "state": {"kind": "lexical-entry", "text": "red", "pos": "adj",
                       "features": {}}})
    r = find_gap_spans(s, "the big red cat sat")
    assert not r.get("ok"), r
    assert r["gaps"], r
    first_gap = r["gaps"][0]
    a, b, seq = first_gap
    assert (a, b) == (0, 3), f"expected gap [0-3], got [{a}-{b}]"
    assert seq == ["det", "adj", "adj", "noun"], seq


def test_gap_analysis_composition_gap():
    """'the cat sat the dog' -> sat is intransitive, can't take an object."""
    from analysis import find_gap_spans
    s = fresh_parse_fixture()
    r = find_gap_spans(s, "the cat sat the dog")
    assert not r.get("ok"), r
    assert not r["gaps"], f"expected no raw gap, got {r['gaps']}"
    assert len(r["maximal"]) >= 2, r["maximal"]


def test_gap_analysis_ok():
    """A parseable sentence returns ok=True."""
    from analysis import find_gap_spans
    s = fresh_parse_fixture()
    r = find_gap_spans(s, "the cat sat")
    assert r.get("ok") is True, r


# --- transitivity --------------------------------------------------------
def test_parse_transitive():
    """'the cat chased the dog' parses via VP -> verb(transitive) NP."""
    from parse import parse_sentence
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat chased the dog")
    assert "error" not in r, r
    assert r["sentence"] is not None, r


def test_parse_transitive_needs_object():
    """'the cat chased' -> transitive verb without object doesn't produce S."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat chased")
    assert "error" not in r, r
    assert r["sentence"] is None, f"expected no S, got {r['sentence']}"
    cleanup_session(s, r["session"])


def test_parse_intransitive_rejects_object():
    """'the cat sat the dog' -> sat is intransitive, no VP -> verb NP."""
    from parse import parse_sentence, cleanup_session
    s = fresh_parse_fixture()
    r = parse_sentence(s, "the cat sat the dog")
    assert "error" not in r, r
    assert r["sentence"] is None, f"expected no full S, got {r['sentence']}"
    cleanup_session(s, r["session"])


# --- number agreement ----------------------------------------------------
def test_number_agreement():
    """'a cats' must fail; 'the cats' must parse."""
    from parse import parse_sentence, cleanup_session
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
    from parse import parse_sentence, cleanup_session
    from feedback import apply_feedback
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
    from parse import parse_sentence, cleanup_session
    from feedback import apply_feedback
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
    from parse import parse_sentence, cleanup_session
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
    from parse import parse_sentence, cleanup_session
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
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
