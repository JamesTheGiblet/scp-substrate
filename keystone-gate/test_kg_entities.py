"""Entities, and sorting old capsules into entities and subjects. Run: python tests/run.py"""
from support_kg import *


def _store():
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity", "foundation:person", "foundation:project"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    knowledge = lambda cid, **st: s.write({"id": cid, "foundation": "foundation:knowledge", "state": st})
    s.write({"id": "james", "foundation": "foundation:person", "state": {"role": "builder"}})
    knowledge("project/robot-arm", kind="project", name="robot-arm", status="active")
    knowledge("qinetiq", kind="organisation", name="QinetiQ")
    knowledge("tool/esp32", kind="tool", name="ESP32")
    knowledge("esp32", kind="tool", name="ESP32")
    knowledge("person/james-gilbert", kind="person")
    s.link("james", "works-at", "qinetiq")
    s.link("james", "uses", "tool/esp32")
    s.link("james", "uses", "esp32")
    s.link("tool/esp32", "used-in", "project/robot-arm")
    s.link("james", "same-as", "person/james-gilbert")
    s.link("person/james-gilbert", "same-as", "james")
    return s


def _accept(s, target, action, **kw):
    from kg_entities import accept_sort, propose_sort
    pid = propose_sort(s, target, action, "claude", **kw)["proposal_id"]
    return accept_sort(s, pid, "james")


def test_nothing_changes_until_accepted():
    from kg_entities import propose_sort
    s = _store()
    try:
        propose_sort(s, "qinetiq", "entity", "claude", kind="organisation", new_id="entity/qinetiq")
        assert s.get("qinetiq")["foundation"] == "foundation:knowledge"
        assert s.get("entity/qinetiq") is None
    finally:
        s.close()


def test_an_entity_can_move_and_keep_its_links():
    s = _store()
    try:
        r = _accept(s, "qinetiq", "entity", kind="organisation", new_id="entity/qinetiq")
        assert r["id"] == "entity/qinetiq"
        assert s.get("qinetiq") is None
        row = s.get("entity/qinetiq")
        assert row["foundation"] == "foundation:entity" and row["state"]["kind"] == "organisation"
        assert {"type": "works-at", "target": "entity/qinetiq"} in [
            {k: l[k] for k in ("type", "target")} for l in s.links_from("james")]
        events = s.conn.execute("SELECT payload FROM events WHERE event_type = 'capsule.renamed' "
                                "AND capsule_id = 'entity/qinetiq'").fetchall()
        assert '"from": "qinetiq"' in events[0][0]
    finally:
        s.close()


def test_a_project_keeps_its_id_and_becomes_a_project():
    s = _store()
    try:
        _accept(s, "project/robot-arm", "entity", kind="project")
        row = s.get("project/robot-arm")
        assert row["foundation"] == "foundation:project" and row["state"]["status"] == "active"
    finally:
        s.close()


def test_a_subject_moves_and_used_in_reads_the_right_way():
    s = _store()
    try:
        assert _accept(s, "tool/esp32", "subject", kind="component")["id"] == "subject/esp32"
        assert s.get("subject/esp32")["foundation"] == "foundation:subject"
        links = [(l["type"], l["target"]) for l in s.links_from("project/robot-arm")]
        assert ("uses", "subject/esp32") in links
        assert not [l for l in s.links_from("subject/esp32") if l["type"] == "used-in"]
    finally:
        s.close()


def test_a_duplicate_merges_without_doubling_links():
    s = _store()
    try:
        _accept(s, "tool/esp32", "subject", kind="component")
        _accept(s, "esp32", "merge", into="subject/esp32")
        assert s.get("esp32") is None
        uses = [l for l in s.links_from("james") if l["type"] == "uses"]
        assert [l["target"] for l in uses] == ["subject/esp32"]
        payload = s.conn.execute("SELECT payload FROM events WHERE event_type = 'capsule.merged'").fetchone()[0]
        assert '"from": "esp32"' in payload and '"name": "ESP32"' in payload
    finally:
        s.close()


def test_a_document_describes_its_entity():
    s = _store()
    try:
        _accept(s, "person/james-gilbert", "describe", into="james")
        links = [(l["type"], l["target"]) for l in s.links_from("james")]
        assert ("described-by", "person/james-gilbert") in links and ("same-as", "person/james-gilbert") not in links
        assert not [l for l in s.links_from("person/james-gilbert") if l["type"] == "same-as"]
    finally:
        s.close()


def test_a_person_can_correct_a_proposal_when_accepting():
    from kg_entities import accept_sort, propose_sort
    s = _store()
    try:
        pid = propose_sort(s, "tool/esp32", "subject", "claude")["proposal_id"]
        r = accept_sort(s, pid, "james", action="entity", entity_kind="board", new_id="entity/my-esp32")
        assert r["id"] == "entity/my-esp32" and s.get("entity/my-esp32")["state"]["kind"] == "board"
        assert "error" in accept_sort(s, pid, "james")
    finally:
        s.close()


def test_a_rejection_sticks_and_changes_nothing():
    from kg_entities import propose_sort, reject_sort
    s = _store()
    try:
        pid = propose_sort(s, "qinetiq", "drop", "claude")["proposal_id"]
        reject_sort(s, pid, "james", reason="keep it")
        assert s.get("qinetiq") is not None
        assert propose_sort(s, "qinetiq", "drop", "claude")["skipped"]
    finally:
        s.close()


def test_entities_and_relations():
    from kg_entities import add_entity, list_entities, relate
    s = _store()
    try:
        assert add_entity(s, "SCPBot", "robot", "james")["id"] == "entity/scpbot"
        assert add_entity(s, "Robot arm v2", "project", "james")["id"] == "project/robot-arm-v2"
        assert "error" in relate(s, "entity/scpbot", "likes", "james")
        assert "error" not in relate(s, "james", "building", "entity/scpbot")
        ids = [e["id"] for e in list_entities(s)]
        assert {"entity/scpbot", "project/robot-arm-v2", "james"} <= set(ids)
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
