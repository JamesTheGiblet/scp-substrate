"""Spec a project from what the store knows. Run: python tests/run.py"""
from support_kg import *


def _store():
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity", "foundation:project"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    return s


def test_a_spec_gives_what_is_known_and_asks_about_the_rest():
    from kg_csv import write
    from kg_spec import spec
    s = _store()
    try:
        write(s, "entity,subject,subject_is_a,uses,claim\n"
                 "Rigbot,MG90S,Servos,yes,Rigbot's MG90S run from a UBEC.\n"
                 "Parts,Servos,,,A servo holds its angle under load.\n", "james")
        r = spec(s, "Desk Arm", ["mg90s", "camera"])
        assert not r["exists"] and r["entity"] == "project/desk-arm"
        found = {cid: others for cid, _, _, others in r["unvalidated"]}
        # The MG90S's own claim says where it came from; the servo claim is general
        assert found["cube/rigbot-s-mg90s-run-from-a-ubec"] == ["Rigbot"], found
        assert found["cube/a-servo-holds-its-angle-under-load"] == ["Parts"], found
        assert not r["known"]
        assert [t for t, _ in r["unknown"]] == ["camera"]
    finally:
        s.close()


def test_what_protects_a_claim_in_the_spec_comes_under_safety():
    from kg_csv import write
    from kg_spec import spec
    from store.claim_links import relate
    s = _store()
    try:
        write(s, "entity,subject,uses,claim,id\n"
                 "Rigbot,UBEC,yes,Rigbot's UBEC feeds the servos.,cube/ubec-feeds\n"
                 "Parts,Fuses,,A fuse stops a short becoming a fire.,cube/fuse\n"
                 "Parts,Fuses,,A fuse must be rated under the wire's limit.,cube/fuse-rating\n", "james")
        relate(s, "cube/fuse", "protects", "cube/ubec-feeds", "james")
        relate(s, "cube/fuse-rating", "limits", "cube/fuse", "james")
        r = spec(s, "Desk Arm", ["ubec"])
        assert [(c, w, o) for c, _, w, o, _ in r["safety"]] == [
            ("cube/fuse", "protects", "cube/ubec-feeds"), ("cube/fuse-rating", "limits", "cube/fuse")], r["safety"]
    finally:
        s.close()


def test_safety_follows_what_risks_a_claim_and_what_solves_that():
    from kg_csv import write
    from kg_spec import spec
    from store.claim_links import relate
    s = _store()
    try:
        write(s, "entity,subject,uses,claim,id\n"
                 "Rigbot,Camera,yes,The camera needs a solid 5V.,cube/cam\n"
                 "Parts,Servos,,Servo stalls pull the supply down.,cube/stall\n"
                 "Rigbot,Supply,,A separate servo supply keeps stalls off the camera.,cube/apart\n"
                 "Rigbot,Camera,,The camera needs 4V.,cube/cam-old\n", "james")
        relate(s, "cube/stall", "risks", "cube/cam", "james")
        relate(s, "cube/apart", "solves", "cube/stall", "james")
        relate(s, "cube/cam", "replaces", "cube/cam-old", "james")
        r = spec(s, "Desk Arm", ["camera"])
        assert [(c, w) for c, _, w, _, _ in r["safety"]] == [("cube/stall", "risks"), ("cube/apart", "solves")], r["safety"]
        # The old claim is out of date, so only the newer one is listed
        assert [c for c, *_ in r["unvalidated"]] == ["cube/cam"], r["unvalidated"]
    finally:
        s.close()


def test_the_question_sheet_imports_only_the_rows_with_a_claim():
    from kg_csv import write
    from kg_spec import sheet, spec
    s = _store()
    try:
        text = sheet("Desk Arm", spec(s, "Desk Arm", ["camera", "lidar"]))
        lines = text.splitlines()
        lines[1] = lines[1].replace(",needs-check", "The camera is an OV2640.,needs-check", 1)
        made = write(s, "\n".join(lines) + "\n", "james")
        assert made["claims"] == ["cube/the-camera-is-an-ov2640"], made
        assert s.get("project/desk-arm") and s.get("subject/camera") and not s.get("subject/lidar")
        assert any(l["target"] == "subject/camera" for l in s.links_from("project/desk-arm") if l["type"] == "uses")
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
