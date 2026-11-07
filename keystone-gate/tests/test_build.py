"""The page's Build panel. Run: python tests/run.py"""
from support_kg import *


def _store():
    from kg_csv import write
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity", "foundation:project"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    write(s, "entity,subject,subject_is_a,uses,claim\n"
             "Rigbot,MG90S,Servos,yes,Rigbot's MG90S run from a UBEC.\n"
             "Rigbot,Servo power,,yes,Servo power needs its own supply.\n", "james")
    return s


def test_a_word_that_matches_two_things_waits_for_a_pick():
    from kg_build import check
    s = _store()
    try:
        r = check(s, "Desk Arm", "servo, camera")
        servo = next(p for p in r["parts"] if p["term"] == "servo")
        assert {m["id"] for m in servo["matches"]} == {"subject/servos", "subject/servo-power"}, servo
        picked = check(s, "Desk Arm", "servo, camera", {"servo": ["subject/servo-power"]})
        servo = next(p for p in picked["parts"] if p["term"] == "servo")
        # The other match is still offered, just not picked
        assert servo["picked"] == ["subject/servo-power"] and len(servo["matches"]) == 2
        assert [c["id"] for c in picked["unvalidated"]] == ["cube/servo-power-needs-its-own-supply"]
        assert [u["term"] for u in picked["unknown"]] == ["camera"]
    finally:
        s.close()


def test_saving_makes_the_project_its_parts_and_your_answers():
    from kg_build import check, save
    s = _store()
    try:
        made = save(s, {"name": "Desk Arm",
                        "parts": [{"term": "mg90s", "ids": ["subject/mg90s"], "count": 6},
                                  {"term": "camera", "ids": [], "count": None}],
                        "answers": [{"term": "camera", "claim": "The desk arm's camera is an OV2640."}]}, "james")
        assert made["project"] == "project/desk-arm" and made["subjects"] == ["subject/camera"], made
        uses = {l["target"] for l in s.links_from("project/desk-arm") if l["type"] == "uses"}
        assert uses == {"subject/mg90s", "subject/camera"}, uses
        assert s.get("project/desk-arm")["state"]["parts"] == {"subject/mg90s": {"count": 6}}
        cid = made["claims"][0]
        about = {l["target"] for l in s.links_from(cid)}
        assert {"subject/camera", "project/desk-arm"} <= about, about
        # Next time, the project's own parts come back without being typed
        again = check(s, "Desk Arm", "")
        assert {p["term"] for p in again["parts"]} == {"MG90S", "Camera"}, again["parts"]
        assert not again["unknown"]
    finally:
        s.close()


def test_an_alias_makes_the_same_words_find_it():
    from kg_build import alias, check
    s = _store()
    try:
        assert check(s, "Desk Arm", "wiggler")["unknown"]
        alias(s, {"id": "subject/mg90s", "alias": "wiggler"}, "james")
        assert alias(s, {"id": "subject/mg90s", "alias": "Wiggler"}, "james")["already"]
        part = check(s, "Desk Arm", "wiggler")["parts"][0]
        assert "subject/mg90s" in part["picked"], part
        for bad in ({"id": "cube/x", "alias": "x"}, {"id": "subject/mg90s", "alias": " "}):
            try:
                alias(s, bad, "james")
                raise AssertionError(f"accepted {bad}")
            except ValueError:
                pass
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
