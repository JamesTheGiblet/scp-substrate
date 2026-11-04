"""Lens links need real shared words, not stock phrases. Run: python tests/run.py"""
from support_kg import *


def _cube(cid, text, lens="CONTEXT", subjects=(), about_you=False, entities=()):
    return {"id": cid, "faces": {lens: {"content": text}}, "subjects": list(subjects),
            "entities": list(entities), "about_you": about_you}


def _pairs(cubes, lens="CONTEXT"):
    from kg_lens_links import cluster
    return {(l["a"], l["b"]) for l in cluster(cubes, (lens,))["links"]}


def test_pronouns_and_the_stores_own_words_do_not_link():
    cubes = [_cube("a", "Attached to the james entity; his linked document."),
             _cube("b", "Attached to the james entity, from his signed person document.")]
    assert _pairs(cubes) == set()


def test_cubes_apart_need_three_shared_words():
    two = [_cube("a", "regulator servo gearbox"), _cube("b", "regulator servo bracket")]
    three = [_cube("a", "regulator servo stall gearbox"), _cube("b", "regulator servo stall bracket")]
    assert _pairs(two) == set() and _pairs(three) == {("a", "b")}


def test_two_words_do_on_a_shared_subject():
    cubes = [_cube("a", "regulator servo gearbox", subjects=["subject/mg90s"]),
             _cube("b", "regulator servo bracket", subjects=["subject/mg90s"])]
    assert _pairs(cubes) == {("a", "b")}


def test_being_about_you_is_not_a_shared_subject():
    cubes = [_cube("a", "regulator servo gearbox", about_you=True, entities=["james"]),
             _cube("b", "regulator servo bracket", about_you=True, entities=["james"])]
    assert _pairs(cubes) == set()


def test_a_word_on_most_faces_is_boilerplate():
    # "suppose" is stopped already; "imagine" opens most of these faces too
    cubes = [_cube(f"c{i}", f"Imagine scenario {i} unfolds {'gearbox' if i < 2 else 'kettle'}", "FICTION")
             for i in range(10)]
    assert _pairs(cubes, "FICTION") == set()


if __name__ == "__main__":
    run_tests(globals())
