"""Substrate tests, part 1 of 4. Run: python tests/run.py"""
from support_substrate import *


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


if __name__ == "__main__":
    run_tests(globals())
