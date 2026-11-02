"""Models draft blanks, and a person decides. Run: python tests/run.py"""
import json

from support_kg import *


def _draft(*pairs, name="gemini"):
    reply = json.dumps({"drafts": [{"lens": l, "content": c} for l, c in pairs]})

    def phrase(ask, known, system, schema, read):
        phrase.ask, phrase.known = ask, known
        return read(reply)
    return name, phrase


def _fails(why):
    def phrase(ask, known, system, schema, read):
        from kg_llm import LLMUnavailable
        raise LLMUnavailable(why)
    return "claude", phrase


def _cube(s, content="A claim to draft", **faces):
    from kg_agent import create_cube, fill_face
    cid = create_cube(s, content)["cube_id"]
    for lens, text in faces.items():
        fill_face(s, cid, lens, text)
    return cid


def test_drafts_are_pending_and_count_for_nothing():
    from kg_agent import completeness, list_proposals
    from kg_fill import blanks, draft_cube
    s = Substrate()
    try:
        cid = _cube(s, FACT="known")
        model = _draft(("COUNTER", "against"), ("OPINION", "a view"))
        r = draft_cube(s, cid, models=[model])
        assert r["drafted"] == ["COUNTER", "OPINION"] and r["by"] == "gemini", r
        assert "known" in model[1].known and "FACT" not in model[1].ask, model[1].ask
        assert completeness(s, cid)["filled_lenses"] == ["FACT"]
        waiting = list_proposals(s, cube_id=cid, status="pending")
        assert {p["proposed_by"] for p in waiting} == {"model-draft:gemini"}
        assert blanks(s, cid) == ["FICTION", "CONTEXT"]
    finally:
        s.close()


def test_a_model_cannot_overwrite_a_filled_face():
    from kg_agent import show_cube
    from kg_fill import draft_cube
    s = Substrate()
    try:
        cid = _cube(s, FACT="mine")
        r = draft_cube(s, cid, models=[_draft(("FACT", "theirs"), ("COUNTER", "against"))])
        assert r["drafted"] == ["COUNTER"], r
        assert show_cube(s, cid)["faces"]["FACT"]["content"] == "mine"
    finally:
        s.close()


def test_the_next_model_drafts_when_one_fails():
    from kg_fill import draft_cube
    s = Substrate()
    try:
        r = draft_cube(s, _cube(s), models=[_fails("no credit"), _draft(("FACT", "known"), name="ollama")])
        assert r["by"] == "ollama" and r["tried"] == ["claude: no credit"], r
    finally:
        s.close()


def test_a_rejected_draft_is_not_offered_again_unchanged():
    from kg_agent import list_proposals, reject_proposal
    from kg_fill import draft_cube
    s = Substrate()
    try:
        cid = _cube(s)
        draft_cube(s, cid, models=[_draft(("FACT", "wrong"))])
        reject_proposal(s, list_proposals(s, cube_id=cid, status="pending")[0]["id"], rejected_by="james")
        r = draft_cube(s, cid, models=[_draft(("FACT", "wrong"))])
        assert r["drafted"] == [] and "nothing new" in r["tried"][0], r
        assert draft_cube(s, cid, models=[_draft(("FACT", "better"))])["drafted"] == ["FACT"]
    finally:
        s.close()


def test_every_model_failing_leaves_the_cube_alone():
    from kg_agent import list_proposals
    from kg_fill import draft_cube
    s = Substrate()
    try:
        cid = _cube(s)
        r = draft_cube(s, cid, models=[_fails("no credit")])
        assert r["drafted"] == [] and list_proposals(s, cube_id=cid, status="pending") == [], r
    finally:
        s.close()


def test_the_background_drafter_reports_failure():
    import threading
    from kg_fill import Drafter

    def broken(s, cube_id, lock):
        raise RuntimeError("no network")
    drafter = Drafter(threading.Lock(), draft=broken)
    drafter.add("cube/x")
    drafter.jobs.join()
    assert "no network" in drafter.error and drafter.waiting() == 0


if __name__ == "__main__":
    run_tests(globals())
