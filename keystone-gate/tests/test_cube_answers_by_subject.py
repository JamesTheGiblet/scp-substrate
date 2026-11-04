"""Asking about a subject or an entity finds the claims linked to it. Run: python tests/run.py"""
from support_kg import *


def _seed():
    """A test robot that uses one part, with a claim about the part that shares
    no words with the question, and a claim that shares a word but no link."""
    from kg_agent import create_cube
    from kg_entities import add_entity, link_claim, relate
    s = Substrate()
    try:
        bot = add_entity(s, "Testbot", "robot", "james", eid="entity/testbot", aliases="Tinkerbot")["id"]
        s.write({"id": "subject/zx-gearmotor", "foundation": "foundation:subject", "state": {"name": "ZX gearmotor"}})
        relate(s, bot, "uses", "subject/zx-gearmotor")
        part = create_cube(s, "It stalls under a heavy load.", cube_id="cube/zx-stalls-under-load")["cube_id"]
        link_claim(s, part, subjects=["subject/zx-gearmotor"])
        create_cube(s, "Plastic gears wear out in time.", cube_id="cube/plastic-gears-wear")
    finally:
        s.close()


_seed()


def _ask(question):
    from kg_hal import ask_gated
    s = Substrate()
    try:
        return ask_gated(s, question)["answer"]
    finally:
        s.close()


def test_an_entity_reaches_the_claims_about_its_parts():
    answer = _ask("what do I know about Testbot's gears")
    assert "on Testbot" in answer, answer
    assert answer.index("cube/zx-stalls-under-load") < answer.index("cube/plastic-gears-wear"), answer
    assert "about: ZX gearmotor" in answer, answer


def test_a_named_subject_ranks_above_a_word_match():
    answer = _ask("what do I know about the zx gearmotor gears")
    assert "on ZX gearmotor" in answer, answer
    assert answer.index("cube/zx-stalls-under-load") < answer.index("cube/plastic-gears-wear"), answer


def test_an_alias_names_the_entity():
    assert "on Testbot" in _ask("what do I believe about tinkerbot")


def test_a_question_naming_nothing_still_matches_words():
    answer = _ask("what do I know about plastic gears wearing")
    assert "cube/plastic-gears-wear" in answer and " on " not in answer.splitlines()[0], answer


if __name__ == "__main__":
    run_tests(globals())
