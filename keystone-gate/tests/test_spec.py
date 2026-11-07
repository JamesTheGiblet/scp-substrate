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
