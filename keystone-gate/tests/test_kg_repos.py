"""Repos as boxes of cubes, and private ones staying home. Run: python tests/run.py"""
import json

from support_kg import *

README = "# Widget\n\nWidget turns   gears into\nsprockets quickly.\n\nIt has no tests yet at all.\n"


def _repo(name="Widget", private=False):
    return {"name": name, "owner": "James", "description": "gears", "private": private,
            "url": "https://example.test", "readme": README}


def _model(name, *claims):
    calls = []

    def phrase(ask, known, system, schema, read):
        calls.append(known)
        return read(json.dumps({"claims": [{"claim": c, "quote": q} for c, q in claims]}))
    phrase.calls = calls
    return name, phrase


GOOD = ("Widget makes sprockets from gears.", "Widget turns gears into sprockets quickly.")


def test_claims_become_cubes_in_a_repo_box():
    from kg_agent import list_proposals, show_cube
    from kg_repos import add_repo
    from kg_view import collect
    s = Substrate()
    try:
        r = add_repo(s, _repo(), models=[_model("gemini", GOOD, ("Made up.", "this line is not in the readme"))])
        assert r["by"] == "gemini" and len(r["cubes"]) == 1, r
        cid = r["cubes"][0]
        assert show_cube(s, cid)["completeness"]["filled_lenses"] == []
        draft = list_proposals(s, cube_id=cid, status="pending")[0]
        assert draft["lens"] == "FACT" and "Widget turns gears" in draft["content"], draft
        cubes = collect(s)
        cube = next(c for c in cubes if c["id"] == cid)
        assert cube["repo"] == "Widget" and cube["group"] == "Widget", cube
    finally:
        s.close()


def test_a_repo_is_not_added_twice():
    from kg_repos import add_repo
    s = Substrate()
    try:
        add_repo(s, _repo("Twice"), models=[_model("gemini", GOOD)])
        model = _model("gemini", GOOD)
        r = add_repo(s, _repo("Twice"), models=[model])
        assert r["cubes"] == [] and model[1].calls == [], r
    finally:
        s.close()


def test_a_private_readme_goes_only_to_a_local_model():
    from kg_repos import add_repo
    s = Substrate()
    try:
        outside, local = _model("gemini", GOOD), _model("ollama", GOOD)
        r = add_repo(s, _repo("Secret", private=True), models=[outside, local])
        assert r["by"] == "ollama" and outside[1].calls == [], r
        s_cube = s.get(r["cubes"][0])
        assert "private" in s_cube["state"]["tags"]
    finally:
        s.close()


def test_a_private_cube_is_only_drafted_locally():
    from kg_fill import DRAFT_SCHEMA, draft_cube
    from kg_repos import add_repo
    s = Substrate()
    try:
        r = add_repo(s, _repo("Secret2", private=True), models=[_model("ollama", GOOD)])
        seen = []

        def phrase(name):
            def run(ask, known, system, schema, read):
                seen.append(name)
                return read(json.dumps({"drafts": [{"lens": "COUNTER", "content": "against"}]}))
            return name, run
        result = draft_cube(s, r["cubes"][0], models=[phrase("gemini"), phrase("ollama")])
        assert seen == ["ollama"] and result["by"] == "ollama", (seen, result)
    finally:
        s.close()


def test_answers_about_private_cubes_stay_local():
    from kg_agent import fill_face
    from kg_llm import mentions_private
    from kg_repos import add_repo
    s = Substrate()
    try:
        r = add_repo(s, _repo("Secret3", private=True), models=[_model("ollama", GOOD)])
        assert mentions_private(s, "Evidence: " + GOOD[0])
        fill_face(s, r["cubes"][0], "OPINION", "my private reasoning about gears")
        assert mentions_private(s, "my private reasoning about gears, it says")
        assert not mentions_private(s, "nothing to do with it")
    finally:
        s.close()


def test_the_repo_mode_boxes_every_cube():
    from kg_lens_links import all_modes
    cubes = [{"id": f"cube/{i}", "faces": {}, "repo": r} for i, r in enumerate(("A", "A", "B", None))]
    mode = all_modes(cubes)["REPOS"]
    names = {c["name"]: c["members"] for c in mode["clusters"]}
    assert names["A"] == ["cube/0", "cube/1"] and names["B"] == ["cube/2"], names
    assert sum(len(m) for m in names.values()) == 4
    assert "REPOS" not in all_modes([{"id": "cube/0", "faces": {}, "repo": None}])


if __name__ == "__main__":
    run_tests(globals())
