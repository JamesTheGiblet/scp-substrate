"""Evidence, and standing made from it and from links between claims. Run: python tests/run.py"""
import sys
from pathlib import Path

from support_kg import *

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


def _store():
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:evidence", "foundation:observation", "foundation:person"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    return s


def _standing(s, cid):
    from store.trust import fused_trust
    return round(fused_trust(s, cid)["posterior"], 2)


def test_a_claim_with_no_evidence_stands_at_a_half():
    from kg_agent import create_cube
    s = _store()
    try:
        cid = create_cube(s, "The UBEC gives 5 V.")["cube_id"]
        assert _standing(s, cid) == 0.5
    finally:
        s.close()


def test_evidence_adds_by_its_kind():
    from kg_agent import create_cube
    from store.evidence import add_evidence, cite, evidence_of
    s = _store()
    try:
        a = create_cube(s, "The UBEC gives 5 V.")["cube_id"]
        b = create_cube(s, "The MG90S has metal gears.")["cube_id"]
        add_evidence(s, "ubec-on-the-meter", "measurement", "UBEC output on the multimeter", "james")
        add_evidence(s, "mg90s-listing", "listing", "A seller's MG90S listing", "james")
        cite(s, a, "evidence/ubec-on-the-meter")
        cite(s, b, "evidence/mg90s-listing")
        # A measurement counts as much as a validation; a listing a quarter of one
        assert _standing(s, a) == 0.73 and _standing(s, b) == 0.56
        assert evidence_of(s, a) == [{"id": "evidence/ubec-on-the-meter", "kind": "measurement",
                                      "weight": 1.0, "title": "UBEC output on the multimeter", "changed": False}]
    finally:
        s.close()


def test_evidence_must_be_real_and_of_a_known_kind():
    from kg_agent import create_cube
    from store.evidence import add_evidence, cite
    s = _store()
    try:
        cid = create_cube(s, "The UBEC gives 5 V.")["cube_id"]
        assert "error" in add_evidence(s, "a-hunch", "hunch", "A hunch", "james")
        assert "error" in cite(s, cid, "evidence/missing")
        # A whole repo is what a claim is about, not evidence for it
        s.write({"id": "repo/x", "foundation": "foundation:knowledge", "state": {"kind": "repo"}})
        assert "error" in cite(s, cid, "repo/x")
        # James's person document is imported as knowledge of kind person, and counts
        s.write({"id": "person/x", "foundation": "foundation:knowledge", "state": {"kind": "person", "title": "X"}})
        assert "error" not in cite(s, cid, "person/x") and _standing(s, cid) == 0.62
        assert add_evidence(s, "readme", "doc", "README", "james")["status"] == "created"
        assert add_evidence(s, "readme", "doc", "README", "james")["status"] == "exists"
    finally:
        s.close()


def _validate(s, cid):
    s.write({"id": f"obs/{cid}", "foundation": "foundation:observation", "state": {"score": 1.0}})
    s.link(f"obs/{cid}", "observes", cid)


def test_a_supporting_claim_raises_standing_and_one_against_lowers_it():
    from kg_agent import create_cube
    from store.claim_links import relate
    s = _store()
    try:
        claim, seen, unseen, doubt = (create_cube(s, t)["cube_id"] for t in (
            "Servos run from the UBEC.", "The PCA9685 doesn't power servos.",
            "The V+ terminal needs its own supply.", "One build powers servos from the board."))
        _validate(s, seen)
        relate(s, seen, "supports", claim, "james")
        assert _standing(s, claim) == 0.62      # +0.5 from a validated claim
        relate(s, unseen, "supports", claim, "james")
        assert _standing(s, claim) == 0.68      # +0.25 more from one nobody has looked at
        relate(s, doubt, "goes against", claim, "james")
        assert _standing(s, claim) == 0.62      # -0.25 from an unvalidated claim against it
    finally:
        s.close()


def test_claims_backing_each_other_cannot_raise_themselves():
    from kg_agent import create_cube
    from store.claim_links import relate
    s = _store()
    try:
        a = create_cube(s, "A is so.")["cube_id"]
        b = create_cube(s, "B is so.")["cube_id"]
        relate(s, a, "supports", b, "james")
        relate(s, b, "supports", a, "james")
        # Each gets one step from the other, and no more
        assert _standing(s, a) == _standing(s, b) == 0.56
    finally:
        s.close()


def test_an_answer_says_what_a_claim_rests_on():
    from answer.walk_cubes import walk_what_believe
    from kg_agent import create_cube
    from store.evidence import add_evidence, cite
    s = _store()
    try:
        a = create_cube(s, "The UBEC gives 5 V.")["cube_id"]
        create_cube(s, "The UBEC runs warm.")
        add_evidence(s, "ubec-on-the-meter", "measurement", "UBEC output on the multimeter", "james")
        cite(s, a, "evidence/ubec-on-the-meter")
        detail = walk_what_believe(s, "james", "ubec")["detail"]
        assert "rests on: UBEC output on the multimeter (measurement)" in detail, detail
        assert "rests on: nothing yet, your word only" in detail, detail
    finally:
        s.close()


def test_source_lines_name_their_evidence():
    from evidence_from_sources import pieces
    ids = lambda src: [p[0] for p in pieces(src)]
    assert ids("Checked against the Replicant repo on 2026-11-03: README.md and CHANGELOG.md v1.0") == [
        "evidence/replicant-readme", "evidence/replicant-changelog"]
    assert ids("Corrected from Claude's draft to match the Replicant repo on 2026-11-03: python/src/world.py, "
               "_decay_claims") == ["evidence/replicant-python-src-world-py"]
    # Files that moved are cited where they are now
    assert ids("Checked against the scp-substrate code on 2026-11-03: src/trust.py, fused_trust") == [
        "evidence/scp-substrate-src-store-trust-py"]
    assert ids("Checked against LLLM's README on 2026-11-03: What it is") == ["evidence/lllm-readme"]
    assert ids("The listing copy and image, and a customer review (Ernestina)") == [
        "evidence/acebott-spider-listing", "evidence/acebott-review-ernestina"]
    assert ids("Stated in James's signed person document") == ["person/james-gilbert"]
    # Someone's word, a model's knowledge, an inference and an unrepeatable search are not evidence
    for src in ("Stated by James on 2026-11-03", "Claude's general knowledge, 2026-11-03",
                "Inferred from the listing images; the listing doesn't say",
                "Checked against the scp-substrate code on 2026-11-03: a search of the code"):
        assert ids(src) == [], src


def test_evidence_counts_half_once_its_file_changes():
    from kg_agent import create_cube
    from store.evidence import add_evidence, changed, checked, cite
    s = _store()
    try:
        cid = create_cube(s, "Standing runs from 0 to 1.")["cube_id"]
        f = {"id": "file/demo/trust.py", "foundation": "foundation:knowledge",
             "state": {"kind": "source-file", "path": "trust.py", "sha256": "aaa"}}
        s.write(f)
        add_evidence(s, "demo-trust", "code", "demo: trust.py", "james", path="trust.py", repo="repo/demo")
        cite(s, cid, "evidence/demo-trust")
        # Never checked: nothing to compare against, so it counts in full
        assert not changed(s, s.get("evidence/demo-trust")) and _standing(s, cid) == 0.68
        assert checked(s, "evidence/demo-trust", "james")["version"] == "aaa"
        assert ("cites-file", "file/demo/trust.py") in [(l["type"], l["target"]) for l in s.links_from("evidence/demo-trust")]
        # Re-indexing finds the file changed
        s.write({**f, "state": {**f["state"], "sha256": "bbb"}})
        assert changed(s, s.get("evidence/demo-trust")) and _standing(s, cid) == 0.59
        # Checked again, it counts in full
        checked(s, "evidence/demo-trust", "james")
        assert _standing(s, cid) == 0.68
        # Gone from the index counts as changed
        with s.conn:
            s.conn.execute("DELETE FROM capsules WHERE id = 'file/demo/trust.py'")
        assert changed(s, s.get("evidence/demo-trust"))
        assert "error" in checked(s, "evidence/demo-trust", "james")
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
