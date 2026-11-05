"""Links that carry a connecting word. Run: python tests/run.py"""
import json

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


def test_the_word_is_the_link_in_the_store():
    from kg_agent import accept_proposal
    s = _fresh_kg_substrate()
    try:
        a, b, pid = _pair(s)
        accept_proposal(s, pid, "james", word="depends on", reverse=True)
        links = [(l["type"], l["target"]) for l in s.links_from(b)]
        assert ("depends-on", a) in links and ("neighbour", a) not in links, links
    finally:
        s.close()


def test_relate_links_two_claims_and_says_who():
    from store.claim_links import relate, relations
    s = _fresh_kg_substrate()
    try:
        a, b, _ = _pair(s)
        assert relate(s, a, "protects", b, "james", note="the fuse blows first") == {"from": a, "word": "protects", "to": b}
        assert relate(s, a, "goes-against", b, "james")["word"] == "goes against"
        meta = json.loads(s.conn.execute("SELECT metadata FROM links WHERE type='protects'").fetchone()[0])
        assert meta["by"] == "james" and meta["note"] == "the fuse blows first"
        assert relations(s, b) == [("goes against", a, False), ("protects", a, False)]
        assert "error" in relate(s, a, "is near", b, "james")
        assert "error" in relate(s, a, "supports", a, "james")
        assert "error" in relate(s, a, "supports", "default-cube", "james")
    finally:
        s.close()


def test_an_answer_says_how_its_claims_connect():
    from answer.walk_cubes import walk_what_believe
    from store.claim_links import relate
    s = _fresh_kg_substrate()
    try:
        a, b, _ = _pair(s)
        relate(s, a, "protects", b, "james")
        detail = walk_what_believe(s, "james", "fuse pack")["detail"]
        assert f"link: this protects {b}" in detail, detail
        detail = walk_what_believe(s, "james", "wire current rating")["detail"]
        assert f"link: {a} protects this" in detail, detail
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
