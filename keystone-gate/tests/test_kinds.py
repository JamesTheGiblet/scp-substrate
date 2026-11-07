"""One subject as a kind of another. Run: python tests/run.py"""
from support_kg import *


def _store():
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    return s


def test_a_kind_reaches_up_and_down_and_refuses_a_loop():
    from kg_csv import write
    from kg_subjects import kind_of
    from store.kinds import broader, narrower
    s = _store()
    try:
        write(s, "entity,subject,subject_is_a,uses,claim\n"
                 "Rigbot,MG90S,Servos,yes,The MG90S has metal gears.\n"
                 "Parts,Servos,Actuators,,A servo holds its angle under load.\n", "james")
        assert broader(s, "subject/mg90s") == {"subject/servos", "subject/actuators"}
        assert narrower(s, "subject/actuators") == {"subject/servos", "subject/mg90s"}
        assert "already a kind of" in kind_of(s, "subject/actuators", "subject/mg90s", "james")["error"]
        assert "not found" in kind_of(s, "subject/mg90s", "subject/nothing", "james")["error"]
        assert "not found" in kind_of(s, "subject/nothing", "Servos", "james")["error"]
        # Named, not given by id, either side is made if new
        kind_of(s, "ESP32-CAM", "Servos", "james")
        kind_of(s, "ESP32-CAM", "Camera", "james")
        assert broader(s, "subject/esp32-cam") == {"subject/servos", "subject/actuators", "subject/camera"}
    finally:
        s.close()


def test_a_question_about_the_robot_finds_what_holds_for_its_kind():
    from kg_csv import write
    from answer.walk_cubes import _reach
    s = _store()
    try:
        write(s, "entity,subject,subject_is_a,uses,claim\n"
                 "Rigbot,MG90S,Servos,yes,The MG90S has metal gears.\n"
                 "Parts,Servos,,,A servo holds its angle under load.\n", "james")
        rig = _reach(s, ["entity/rigbot"])["entity/rigbot"]
        assert {"subject/mg90s", "subject/servos"} <= rig, rig
        assert "subject/mg90s" in _reach(s, ["subject/servos"])["subject/servos"]
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
