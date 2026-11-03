"""Foundational cubes follow rules the code enforces. Run: python tests/run.py"""
from support_kg import *

LENSES = ("FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT")


def _cube(s, name, faces=LENSES):
    from kg_agent import create_cube, fill_face
    cid = create_cube(s, name, tags=["foundational"])["cube_id"]
    for lens in faces:
        fill_face(s, cid, lens, f"{lens} in my own words")
    return cid


def test_a_foundational_face_cannot_be_bulk_accepted():
    from kg_agent import accept_proposal, create_cube, propose_face, show_cube
    s = Substrate()
    try:
        cid = create_cube(s, "A rigid claim to accept", tags=["foundational"])["cube_id"]
        pid = propose_face(s, cid, "FACT", "a draft", "model-draft:claude")["proposal_id"]
        r = accept_proposal(s, pid, "james (bulk accept, not read line by line)")
        assert "error" in r and "foundational" in r["error"], r
        assert show_cube(s, cid)["faces"]["FACT"] is None
        assert accept_proposal(s, pid, "james")["status"] == "accepted"
    finally:
        s.close()


def test_an_ordinary_cube_can_still_be_bulk_accepted():
    from kg_agent import accept_proposal, create_cube, propose_face
    s = Substrate()
    try:
        cid = create_cube(s, "An ordinary claim to accept")["cube_id"]
        pid = propose_face(s, cid, "FACT", "a draft", "model-draft:claude")["proposal_id"]
        assert accept_proposal(s, pid, "james (bulk accept, not read line by line)")["status"] == "accepted"
    finally:
        s.close()


def test_a_foundational_cube_needs_all_five_faces_to_validate():
    from kg_agent import validate
    s = Substrate()
    try:
        cid = _cube(s, "A rigid claim with gaps", ("FACT", "COUNTER"))
        r = validate(s, cid, "james", note="holds")
        assert "error" in r and "five" in r["error"], r
        cid = _cube(s, "A rigid claim complete")
        assert "error" not in validate(s, cid, "james", note="holds")
    finally:
        s.close()


def test_a_foundational_note_must_be_the_persons_own():
    from kg_agent import validate
    s = Substrate()
    try:
        cid = _cube(s, "A rigid claim with a draft note")
        assert "error" in validate(s, cid, "james", note=None)
        assert "error" in validate(s, cid, "james", note="   ")
        s.write({"id": f"{cid}/validation-draft", "foundation": "foundation:knowledge",
                 "state": {"kind": "validation-draft", "cube_id": cid, "content": "Suggested words."}})
        r = validate(s, cid, "james", note="  suggested WORDS. ")
        assert "error" in r and "own words" in r["error"], r
        assert "error" not in validate(s, cid, "james", note="I checked this myself.")
    finally:
        s.close()


def test_models_cannot_draft_or_suggest_for_a_foundational_cube():
    from kg_agent import create_cube, list_proposals
    from kg_fill import draft_cube, suggest_note

    def never(*a, **k):
        raise AssertionError("a model was called")
    s = Substrate()
    try:
        cid = create_cube(s, "A rigid blank claim", tags=["foundational"])["cube_id"]
        r = draft_cube(s, cid, models=[("gemini", never)])
        assert r["drafted"] == [] and "foundational" in r["tried"][0], r
        n = suggest_note(s, cid, models=[("gemini", never)])
        assert n["note"] is None and "foundational" in n["tried"][0], n
        assert list_proposals(s, cube_id=cid, status="pending") == []
    finally:
        s.close()


def test_the_page_gets_the_foundational_tag():
    from kg_view import collect
    s = Substrate()
    try:
        cid = _cube(s, "A rigid claim for the page")
        cube = next(c for c in collect(s) if c["id"] == cid)
        assert "foundational" in cube["tags"]
    finally:
        s.close()


def test_safety_becomes_foundational_and_security_is_seeded():
    from kg_agent import create_cube
    from seed_cubes_security import CUBES, mark_foundational, seed
    s = Substrate()
    try:
        cid = create_cube(s, "A safety claim to mark", tags=["safety"])["cube_id"]
        assert mark_foundational(s) >= 1
        assert "foundational" in s.get(cid)["state"]["tags"]
        assert mark_foundational(s) == 0
        seed(s)
        assert seed(s) == []
        assert "foundational" in s.get(f"cube/{CUBES[0][0]}")["state"]["tags"]
    finally:
        s.close()


def test_the_password_hash_meets_the_higher_cost():
    from kg_lock import make_lock, matches
    lock = make_lock("correct horse")
    assert lock["n"] >= 2 ** 17 and matches("correct horse", lock)
    old = {"salt": "00", "hash": "", "n": 2 ** 15, "r": 8, "p": 1}
    import hashlib
    salt = bytes.fromhex("00" * 16)
    old.update(salt=salt.hex(), hash=hashlib.scrypt(b"old password", salt=salt, n=2 ** 15, r=8, p=1, maxmem=2 ** 28).hex())
    assert matches("old password", old), "a password set before the change still works"


if __name__ == "__main__":
    run_tests(globals())
