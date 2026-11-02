"""Asking about cubes returns what is in them. Run: python tests/run.py"""
from support_kg import *


def _ask(question):
    from kg_hal import ask_gated
    s = Substrate()
    try:
        return ask_gated(s, question)
    finally:
        s.close()


def test_believe_returns_claim_view_and_counter():
    r = _ask("what do I believe about signing")
    assert "answer" in r, r
    assert "cube/signed-means-provenance-not-trust" in r["answer"], r
    assert "view:" in r["answer"] and "against:" in r["answer"], r
    assert "standing" in r["answer"], r


def test_signing_does_not_match_signal():
    r = _ask("what do I believe about signing")
    assert "cube/pca9685-" not in r["answer"], r


def test_should_i_finds_the_relevant_cube():
    r = _ask("should I split kg_agent")
    assert "cube/split-files-over-400-lines" in r["answer"], r
    assert "cube/agent-proposes-humans-decide" not in r["answer"], r


def test_unwritten_opinion_says_so():
    r = _ask("what do I think about capsules")
    assert "not written yet" in r["answer"], r


def test_trust_lists_only_attested_cubes():
    from walk_cubes import walk_what_believe
    s = Substrate()
    try:
        r = walk_what_believe(s, None, "what do i trust")
        cubes = [l.split(":")[0].strip() for l in r["detail"].splitlines()]
        assert cubes and all(s.get(f"{c}/attestation") for c in cubes), r
    finally:
        s.close()


def test_retracted_attestation_is_shown_as_retracted():
    from kg_agent import attest, fill_face
    from walk_cubes import walk_what_believe
    s = Substrate()
    try:
        cid = "cube/british-english-everywhere"
        fill_face(s, cid, "FACT", "changed for this test")
        r = walk_what_believe(s, None, "what do i think about british english")
        assert "attestation retracted" in r["detail"], r
    finally:
        s.close()


def test_no_matching_cube_is_stated():
    r = _ask("what do I think about magnets")
    assert "No cube covers that" in r["answer"], r


def test_hardware_cubes_are_answerable_and_sourced():
    r = _ask("what do I know about servo power")
    assert "cube/pca9685-" in r["answer"], r
    s = Substrate()
    try:
        links = s.links_from("cube/pca9685-v-plus-voltage-limit")
        assert any(l["type"] == "derived-from" for l in links), links
    finally:
        s.close()


def test_review_can_filter_by_tag():
    from kg_review import review
    s = Substrate()
    try:
        seen = []
        def show(text):
            if text.startswith("\n==="):
                seen.append(text)
        def ask(prompt):
            raise EOFError
        try:
            review(s, "james", tag="pca9685", ask=ask, show=show)
        except EOFError:
            pass
        assert seen and "cube/pca9685-" in seen[0], seen
    finally:
        s.close()


def test_view_collects_every_cube_with_six_sides():
    from kg_view import collect
    s = Substrate()
    try:
        cubes = collect(s)
        count = s.conn.execute(
            "SELECT COUNT(*) FROM capsules WHERE foundation='foundation:cube'").fetchone()[0]
        assert len(cubes) == count
        assert all(set(c["faces"]) == {"FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"}
                   for c in cubes)
        assert {c["status"] for c in cubes} >= {"attested", "draft"}
        assert any(f and f["unread"] for c in cubes for f in c["faces"].values())
    finally:
        s.close()


def test_view_stored_text_cannot_break_out_of_the_script():
    from kg_view import render
    page = render([{"content": "</script><script>alert(1)</script>"}])
    assert "alert(1)</script>" not in page, page[-300:]
    assert "/*CUBES*/" not in page


def test_view_needs_no_network():
    from kg_view import render
    page = render([])
    for marker in ("http://", "https://", "<link", " src="):
        assert marker not in page, marker


def test_view_has_a_screenshot_button():
    from kg_view import render
    page = render([])
    assert 'id="snap"' in page and "cubeField.snapshot()" in page
    assert "snapshot()" in page.split("window.cubeField")[1]


def _lens_cube(cid, **faces):
    return {"id": cid, "faces": {k: {"content": v} for k, v in faces.items()}}


def test_shared_counter_links_cubes_across_topics():
    from kg_lens_links import cluster
    cubes = [_lens_cube("a", COUNTER="voltage sag under stall load"),
             _lens_cube("b", COUNTER="stall voltage sag at the far joint"),
             _lens_cube("c", COUNTER="keys leaked through backups")]
    result = cluster(cubes, ("COUNTER",))
    assert [(l["a"], l["b"], l["lens"]) for l in result["links"]] == [("a", "b", "COUNTER")]
    names = {tuple(g["members"]) for g in result["clusters"]}
    assert ("a", "b") in names and ("c",) in names, names


def test_clustering_is_repeatable_across_runs():
    import subprocess
    code = (
        "import sys, json\n"
        "sys.path[:0] = [r'%s', r'%s']\n"
        "from kg_lens_links import cluster\n"
        "cubes = [{'id': c, 'faces': {'COUNTER': {'content': 'voltage sag stall wiring supply ' + c}}} for c in 'abcdef']\n"
        "print(json.dumps(cluster(cubes, ('COUNTER',)), sort_keys=True))\n"
    ) % (str(_here.parent / "src"), str(_here))
    runs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env={**os.environ, "PYTHONHASHSEED": seed}).stdout for seed in ("1", "2", "3")}
    assert len(runs) == 1 and runs != {""}, runs


def test_cluster_names_are_real_words():
    from kg_lens_links import cluster
    cubes = [_lens_cube("a", COUNTER="wiring refused supplies"), _lens_cube("b", COUNTER="wiring refused supplies")]
    name = cluster(cubes, ("COUNTER",))["clusters"][0]["name"]
    assert "wir " not in name + " " and "refus " not in name + " ", name


def test_same_word_on_different_lenses_does_not_link():
    from kg_lens_links import cluster
    cubes = [_lens_cube("a", FACT="voltage sag under stall load"),
             _lens_cube("b", COUNTER="voltage sag under stall load")]
    assert cluster(cubes, ("FACT", "COUNTER"))["links"] == []


def test_every_cube_lands_in_exactly_one_cluster():
    from kg_lens_links import all_modes
    from kg_view import collect
    s = Substrate()
    try:
        cubes = collect(s)
        for mode, data in all_modes(cubes).items():
            members = [m for g in data["clusters"] for m in g["members"]]
            assert sorted(members) == sorted(c["id"] for c in cubes), mode
    finally:
        s.close()


def test_pending_drafts_are_not_filled_faces():
    from kg_agent import create_cube, propose_face
    from kg_view import collect
    s = Substrate()
    try:
        cid = create_cube(s, "A claim with only a draft")["cube_id"]
        propose_face(s, cid, "OPINION", "a suggested view", "test")
        cube = next(c for c in collect(s) if c["id"] == cid)
        assert cube["faces"]["OPINION"]["pending"] is True
        assert cube["score"] == 0.0, cube["score"]
    finally:
        s.close()


def test_what_is_shows_the_claim():
    r = _ask("what is cube/british-english-everywhere")
    assert "British English everywhere" in r["answer"], r


if __name__ == "__main__":
    run_tests(globals())
