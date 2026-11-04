"""Cube weights and rules come from default-cube. Run: python tests/run.py"""
import json

from support_kg import *


def _shaped(per_lens, human, minimum):
    s = _fresh_kg_substrate()
    s.write({"id": "default-cube", "foundation": "foundation:knowledge", "state": {
        "weighting": {"per_lens": per_lens, "human_validation": human},
        "rules": {"minimum_lenses": minimum},
    }})
    return s


def test_completeness_reads_weights_from_default_cube():
    from kg_agent import completeness, create_cube, fill_face
    s = _shaped(0.10, 0.50, 0)
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        fill_face(s, cid, "FACT", "x")
        assert abs(completeness(s, cid)["score"] - 0.10) < 1e-6
    finally:
        s.close()


def test_validation_needs_minimum_lenses():
    from kg_agent import create_cube, fill_face, validate
    s = _shaped(0.16, 0.20, 2)
    try:
        cid = create_cube(s, "test cube")["cube_id"]
        fill_face(s, cid, "FACT", "x")
        assert "error" in validate(s, cid, "james")
        fill_face(s, cid, "COUNTER", "y")
        assert "error" not in validate(s, cid, "james")
    finally:
        s.close()


def test_live_default_cube_still_adds_up_to_one():
    s = Substrate()
    try:
        w = s.get("default-cube")["state"]["weighting"]
        assert abs(w["per_lens"] * 5 + w["human_validation"] - 1.0) < 1e-9
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
