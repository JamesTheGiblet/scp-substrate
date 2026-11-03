"""The public snapshot carries nothing private. Run: python tests/run.py"""
import tempfile
from pathlib import Path

from support_kg import *

PRIVATE = ["secret-repo"]


def _snapshot(s):
    from kg_public import write_snapshot
    path = Path(tempfile.mkdtemp(prefix="kg-public-")) / "index.html"
    result = write_snapshot(s, path, private=PRIVATE)
    return result, path.read_text(encoding="utf-8")


def _cube(s, claim, tags=None):
    from kg_agent import create_cube
    return create_cube(s, claim, tags=tags or [])["cube_id"]


def test_private_cubes_and_ones_naming_a_private_repo_stay_out():
    from kg_agent import fill_face
    s = Substrate()
    try:
        shown = _cube(s, "A servo stalls under load, snapshot test")
        hidden = _cube(s, "A personal note for the snapshot test", ["private"])
        named = _cube(s, "Ordinary claim for the snapshot test")
        fill_face(s, named, "CONTEXT", "This came out of Secret-Repo last spring.")
        result, page = _snapshot(s)
        assert shown in page
        assert hidden not in page and "A personal note for the snapshot test" not in page
        assert named not in page and "came out of Secret-Repo" not in page
        assert result["left_out"] >= 2
    finally:
        s.close()


def test_unconfirmed_drafts_stay_out_but_accepted_words_go_in():
    from kg_agent import fill_face, propose_face
    s = Substrate()
    try:
        cid = _cube(s, "A claim with a draft, snapshot test")
        fill_face(s, cid, "FACT", "Words James wrote himself for the snapshot.")
        propose_face(s, cid, "COUNTER", "An unread model draft for the snapshot.", "model-draft:test")
        page = _snapshot(s)[1]
        assert "Words James wrote himself for the snapshot." in page
        assert "An unread model draft for the snapshot." not in page
    finally:
        s.close()


def test_a_link_to_a_hidden_cube_is_cut():
    from kg_public import public_cubes
    base = {"content": "x", "source": "", "group": "g", "repo": None, "note_draft": None,
            "faces": {}, "validation": None, "attestation": None, "contradicts": None}
    cubes = [{**base, "id": "cube/open", "tags": [], "neighbours": ["cube/shut"], "contradicts": "cube/shut"},
             {**base, "id": "cube/shut", "tags": ["private"], "neighbours": ["cube/open"]}]
    kept = public_cubes(cubes, PRIVATE)
    assert [c["id"] for c in kept] == ["cube/open"]
    assert kept[0]["neighbours"] == [] and kept[0]["contradicts"] is None


def test_the_snapshot_cannot_edit():
    s = Substrate()
    try:
        page = _snapshot(s)[1]
        assert "const api = null;" in page and '"token"' not in page
    finally:
        s.close()


def test_no_github_means_no_snapshot():
    import subprocess
    from unittest import mock
    from kg_public import private_repos
    s = Substrate()
    try:
        failed = subprocess.CompletedProcess([], 1, "", "not logged in")
        with mock.patch("kg_public.subprocess.run", return_value=failed):
            try:
                private_repos(s)
            except RuntimeError as e:
                assert "could not list repos" in str(e)
            else:
                raise AssertionError("a failed repo list must stop the snapshot")
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
