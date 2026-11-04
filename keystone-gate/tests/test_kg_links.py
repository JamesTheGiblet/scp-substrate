"""Links that carry a connecting word. Run: python tests/run.py"""
from support_kg import *


def _pair(s):
    from kg_agent import create_cube, propose_neighbour
    a = create_cube(s, "A fuse near the pack")["cube_id"]
    b = create_cube(s, "The wire's current rating")["cube_id"]
    return a, b, propose_neighbour(s, a, b, "model-draft:test", rationale="test")["proposal_id"]


def test_a_link_keeps_its_word_and_direction():
    from kg_agent import accept_proposal
    from kg_view import collect
    s = _fresh_kg_substrate()
    try:
        a, b, pid = _pair(s)
        assert accept_proposal(s, pid, "james", word="protects")["status"] == "accepted"
        cubes = {c["id"]: c for c in collect(s)}
        said = {"word": "protects", "from": a}
        assert cubes[a]["link_words"] == {b: said} and cubes[b]["link_words"] == {a: said}
    finally:
        s.close()


def test_a_link_can_read_the_other_way():
    from kg_agent import accept_proposal
    s = _fresh_kg_substrate()
    try:
        a, b, pid = _pair(s)
        accept_proposal(s, pid, "james", word="depends on", reverse=True)
        assert s.get(pid)["state"]["from"] == b
    finally:
        s.close()


def test_only_the_listed_words_are_allowed():
    from kg_agent import CONNECTING_WORDS, accept_proposal, create_cube, propose_face
    s = _fresh_kg_substrate()
    try:
        a, b, pid = _pair(s)
        r = accept_proposal(s, pid, "james", word="is vaguely related to")
        assert "error" in r and "protects" in r["error"], r
        assert s.get(pid)["state"]["status"] == "pending"
        # A face is not a link, so it takes no connecting word
        fid = propose_face(s, a, "FACT", "a draft", "model-draft:test")["proposal_id"]
        assert "error" in accept_proposal(s, fid, "james", word=CONNECTING_WORDS[0])
    finally:
        s.close()


def test_a_link_without_a_word_still_works():
    from kg_agent import accept_proposal
    from kg_view import collect
    s = _fresh_kg_substrate()
    try:
        a, b, pid = _pair(s)
        assert accept_proposal(s, pid, "james")["status"] == "accepted"
        cube = next(c for c in collect(s) if c["id"] == a)
        assert b in cube["neighbours"] and cube["link_words"] == {}
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
