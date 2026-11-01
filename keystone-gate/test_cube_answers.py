"""Asking about cubes returns what is in them. Run: python tests/run.py"""
from support_kg import *


def _ask(question):
    from kg_hal import ask_gated
    s = Substrate()
    try:
        return ask_gated(s, question)
    finally:
        s.close()


def test_believe_returns_claim_view_and_counter():
    r = _ask("what do I believe about signing")
    assert "answer" in r, r
    assert "cube/signed-means-provenance-not-trust" in r["answer"], r
    assert "view:" in r["answer"] and "against:" in r["answer"], r
    assert "standing" in r["answer"], r


def test_signing_does_not_match_signal():
    r = _ask("what do I believe about signing")
    assert "cube/pca9685-" not in r["answer"], r


def test_should_i_finds_the_relevant_cube():
    r = _ask("should I split kg_agent")
    assert "cube/split-files-over-400-lines" in r["answer"], r
    assert "cube/agent-proposes-humans-decide" not in r["answer"], r


def test_unwritten_opinion_says_so():
    r = _ask("what do I think about capsules")
    assert "not written yet" in r["answer"], r


def test_trust_lists_only_attested_cubes():
    from walk_cubes import walk_what_believe
    s = Substrate()
    try:
        r = walk_what_believe(s, None, "what do i trust")
        cubes = [l.split(":")[0].strip() for l in r["detail"].splitlines()]
        assert cubes and all(s.get(f"{c}/attestation") for c in cubes), r
    finally:
        s.close()


def test_retracted_attestation_is_shown_as_retracted():
    from kg_agent import attest, fill_face
    from walk_cubes import walk_what_believe
    s = Substrate()
    try:
        cid = "cube/british-english-everywhere"
        fill_face(s, cid, "FACT", "changed for this test")
        r = walk_what_believe(s, None, "what do i think about british english")
        assert "attestation retracted" in r["detail"], r
    finally:
        s.close()


def test_no_matching_cube_is_stated():
    r = _ask("what do I think about magnets")
    assert "No cube covers that" in r["answer"], r


def test_hardware_cubes_are_answerable_and_sourced():
    r = _ask("what do I know about servo power")
    assert "cube/pca9685-" in r["answer"], r
    s = Substrate()
    try:
        links = s.links_from("cube/pca9685-v-plus-voltage-limit")
        assert any(l["type"] == "derived-from" for l in links), links
    finally:
        s.close()


def test_review_can_filter_by_tag():
    from kg_review import review
    s = Substrate()
    try:
        seen = []
        def show(text):
            if text.startswith("\n==="):
                seen.append(text)
        def ask(prompt):
            raise EOFError
        try:
            review(s, "james", tag="pca9685", ask=ask, show=show)
        except EOFError:
            pass
        assert seen and "cube/pca9685-" in seen[0], seen
    finally:
        s.close()


def test_what_is_shows_the_claim():
    r = _ask("what is cube/british-english-everywhere")
    assert "British English everywhere" in r["answer"], r


if __name__ == "__main__":
    run_tests(globals())
