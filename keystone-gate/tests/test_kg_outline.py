"""Building an entity, its subjects and claims from an outline. Run: python tests/run.py"""
from support_kg import *

OUTLINE = """
# entity Rover
id: entity/rover
kind: robot
building: james

### claim Rover is a test robot.

## subject Wheel motor
kind: component
uses: yes

### claim A wheel motor needs a driver board.
also: subject/battery
tags: needs-check
FACT: Motors draw more current than a pin can give.

## subject Battery
kind: component
"""


def _store():
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity", "foundation:person"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    s.write({"id": "james", "foundation": "foundation:person", "state": {}})
    return s


def test_an_outline_builds_its_entity_subjects_and_claims():
    from kg_outline import apply, parse
    from kg_proposals import list_proposals
    s = _store()
    try:
        made = apply(s, parse(OUTLINE), "james")
        assert made["entities"] == ["entity/rover"] and made["subjects"] == ["subject/wheel-motor", "subject/battery"]
        assert len(made["claims"]) == 2 and made["drafts"] == 1
        assert ("building", "entity/rover") in [(l["type"], l["target"]) for l in s.links_from("james")]
        assert ("uses", "subject/wheel-motor") in [(l["type"], l["target"]) for l in s.links_from("entity/rover")]
        motor = next(c for c in made["claims"] if "wheel" in c)
        assert "needs-check" in s.get(motor)["state"]["tags"]
        assert {"subject/wheel-motor", "subject/battery"} <= {l["target"] for l in s.links_from(motor)}
        assert not s.get(f"{motor}/face/FACT"), "a lens line is a draft, not a face"
        assert [p["lens"] for p in list_proposals(s, cube_id=motor, status="pending")] == ["FACT"]
        assert apply(s, parse(OUTLINE), "james")["skipped"] == made["claims"]
    finally:
        s.close()


def test_a_bad_reference_writes_nothing():
    from kg_outline import apply, parse
    s = _store()
    try:
        bad = OUTLINE.replace("tags: needs-check", "tags: needs-check\nfrom: docs/nowhere")
        try:
            apply(s, parse(bad), "james")
            raise AssertionError("should have refused")
        except ValueError as e:
            assert "docs/nowhere" in str(e)
        assert s.get("entity/rover") is None
    finally:
        s.close()


def test_a_lens_line_belongs_under_a_claim():
    from kg_outline import parse
    try:
        parse("# entity Rover\n## subject Wheel\nFACT: loose\n")
        raise AssertionError("should have refused")
    except ValueError as e:
        assert "under a ### claim" in str(e)


def test_an_outline_needs_an_entity_first():
    from kg_outline import parse
    try:
        parse("## subject Loose\n")
        raise AssertionError("should have refused")
    except ValueError as e:
        assert "after an # entity" in str(e)


if __name__ == "__main__":
    run_tests(globals())
