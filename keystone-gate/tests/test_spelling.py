"""A misspelt question still finds its claims. Run: python tests/run.py"""
from support_kg import *


def _store():
    from kg_agent import create_cube
    s = _fresh_kg_substrate()
    create_cube(s, "The UBEC steps the pack down to 5 V for the servos.")
    create_cube(s, "The chassis stands 82 mm tall.")
    s.write({"id": "typo/teh", "foundation": "foundation:knowledge", "state": {"kind": "typo", "alias_for": "the"}})
    s.write({"id": "lex/tell", "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "tell"}})
    return s


def test_a_swapped_or_missing_letter_reads_as_the_stores_word():
    from answer.spelling import correct
    s = _store()
    try:
        assert correct(s, "the ubce and the chasis")[1] == [("ubce", "ubec"), ("chasis", "chassis")]
        assert correct(s, "teh servos")[0] == "the servos"
    finally:
        s.close()


def test_real_words_and_guesses_are_left_alone():
    from answer.spelling import correct
    s = _store()
    try:
        # tell is in the lexicon, so it is not read as tall
        assert correct(s, "tell me")[1] == []
        # two edits in a short word is too far to guess
        assert correct(s, "the batrey")[1] == []
    finally:
        s.close()


def test_an_answer_says_what_it_read_a_word_as():
    from answer.walk_cubes import walk_what_believe
    s = _store()
    try:
        r = walk_what_believe(s, "james", "the ubce")
        assert r["summary"].startswith('Read "ubce" as "ubec".'), r
        assert "ubec" in r["detail"].lower()
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
