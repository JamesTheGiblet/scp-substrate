"""Overlaps valued by Leighton weight. Run: python tests/run.py"""
from datetime import datetime, timedelta, timezone

from support_kg import *

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)
STAMP = "2026-11-03T00:00:00Z"
SAME = "servo brownout resets the controller whenever supply voltage sags under stall current"


def _cube(cid, text, home="A", at=STAMP, pending=False):
    fact = {"content": text, "at": at}
    if pending:
        fact["pending"] = True
    return {"id": cid, "repo": home, "group": home, "faces": {"FACT": fact}}


def _filler():
    words = "alpha bravo charlie delta echo foxtrot golf hotel".split()
    return [_cube(f"cube/f{i}", f"{w} {w}x {w}y {w}z", f"F{i}") for i, w in enumerate(words)]


def _pair(**kw):
    return [_cube("cube/a", SAME, "A", **kw), _cube("cube/b", SAME, "B", **kw)] + _filler()


def test_lambda_is_a_decayed_weight_in_range():
    from kg_overlaps import HALF_LIFE_DAYS, find_overlaps
    fresh = find_overlaps(_pair(), now=NOW, minimum=0)[0]
    old = find_overlaps(_pair(), now=NOW + timedelta(days=HALF_LIFE_DAYS), minimum=0)[0]
    assert 0 < fresh["lambda"] <= 2.0, fresh
    assert abs(old["lambda"] - fresh["lambda"] / 2) < .02, (fresh, old)


def test_nothing_below_the_threshold_is_shown():
    from kg_overlaps import THRESHOLD, find_overlaps
    assert THRESHOLD == .60
    assert find_overlaps(_pair(), now=NOW)
    assert find_overlaps(_pair(), now=NOW + timedelta(days=600)) == []


def test_only_different_sources_overlap():
    from kg_overlaps import find_overlaps
    cubes = [_cube("cube/a", SAME, "A"), _cube("cube/b", SAME, "A")] + _filler()
    assert find_overlaps(cubes, now=NOW, minimum=0) == []


def test_pending_drafts_do_not_count():
    from kg_overlaps import find_overlaps
    assert find_overlaps(_pair(pending=True), now=NOW, minimum=0) == []


def test_confirming_adds_weight_and_restarts_the_clock():
    from kg_overlaps import CONFIRM_GAIN, _pair_id, find_overlaps
    later = NOW + timedelta(days=120)
    before = find_overlaps(_pair(), now=later, minimum=0)[0]
    decided = {_pair_id("cube/a", "cube/b"): {"verdict": "confirmed", "decided_at": "2026-11-03T00:00:00Z"}}
    assert find_overlaps(_pair(), decided, now=NOW, minimum=0)[0]["confirmed"]
    fresh = {_pair_id("cube/a", "cube/b"): {"verdict": "confirmed",
                                            "decided_at": later.strftime("%Y-%m-%dT%H:%M:%SZ")}}
    after = find_overlaps(_pair(), fresh, now=later, minimum=0)[0]
    assert after["lambda"] > before["lambda"] + CONFIRM_GAIN, (before, after)


def test_dismissing_hides_it_for_good():
    from kg_overlaps import _pair_id, find_overlaps
    decided = {_pair_id("cube/a", "cube/b"): {"verdict": "dismissed"}}
    assert find_overlaps(_pair(), decided, now=NOW, minimum=0) == []


def test_decisions_are_stored_and_checked():
    from kg_agent import create_cube
    from kg_overlaps import decide, load_decisions
    s = Substrate()
    try:
        a = create_cube(s, "Overlap test one")["cube_id"]
        b = create_cube(s, "Overlap test two")["cube_id"]
        assert "error" in decide(s, a, b, "maybe", "james")
        assert "error" in decide(s, a, "cube/nope", "confirmed", "james")
        made = decide(s, a, b, "confirmed", "james")
        assert load_decisions(s)[made["overlap_id"]]["verdict"] == "confirmed"
        assert decide(s, b, a, "dismissed", "james") == made
        assert load_decisions(s)[made["overlap_id"]]["verdict"] == "dismissed"
    finally:
        s.close()


def test_the_page_gets_overlaps_and_a_box_for_them():
    from kg_lens_links import all_modes
    from kg_overlaps import attach_overlaps
    cubes = attach_overlaps(_pair(), now=NOW)
    assert cubes[0]["overlaps"][0]["other"] == "cube/b"
    mode = all_modes(cubes)["OVERLAPS"]
    boxes = {tuple(c["members"]) for c in mode["clusters"]}
    assert ("cube/a", "cube/b") in boxes and len(mode["links"]) == 1
    assert sum(len(c["members"]) for c in mode["clusters"]) == len(cubes)
    assert "OVERLAPS" not in all_modes(attach_overlaps(_filler(), now=NOW))


if __name__ == "__main__":
    run_tests(globals())
