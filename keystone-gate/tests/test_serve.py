"""The browser's way in: writes need the token and the password. Run: python tests/run.py"""
import http.client
import json
import threading

from support_kg import *

PASSWORD = "correct horse"


class _Server:
    def __init__(self, hosts=()):
        self.hosts = hosts

    def __enter__(self):
        from kg_lock import make_lock
        from kg_serve import make_server
        def draft(s, cube_id, lock):
            from kg_agent import propose_face
            with lock:
                propose_face(s, cube_id, "FACT", "a drafted fact", "model-draft:test")
            return {"drafted": ["FACT"], "by": "test", "tried": []}
        self.server = make_server("james", make_lock(PASSWORD), 0, draft=draft, hosts=self.hosts)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.key = self.unlock(PASSWORD)[1]["key"]
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()

    def request(self, path, data, token=None, host=None, origin=None, key=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json", "Host": host or f"127.0.0.1:{self.port}"}
        if token is not False:
            headers["X-Cube-Token"] = token or self.server.token
        if key:
            headers["X-Cube-Key"] = key
        if origin:
            headers["Origin"] = origin
        conn.request("POST", path, json.dumps(data), headers)
        res = conn.getresponse()
        return res.status, json.loads(res.read())

    def post(self, data, key=None, **kw):
        return self.request("/api/do", data, key=self.key if key is None else key, **kw)

    def unlock(self, password, **kw):
        return self.request("/api/unlock", {"password": password}, **kw)

    def page(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("GET", "/")
        res = conn.getresponse()
        return res.status, res.read().decode("utf-8")


def test_page_carries_the_token_and_edit_tools():
    with _Server() as srv:
        status, page = srv.page()
        assert status == 200
        assert srv.server.token in page and 'id="addcube"' in page


def test_writes_are_refused_without_the_right_token():
    with _Server() as srv:
        body = {"action": "new", "content": "should not exist"}
        assert srv.post(body, token=False)[0] == 403
        assert srv.post(body, token="wrong")[0] == 403
        assert srv.post(body, token="wrongé")[0] in (400, 403)
        s = Substrate()
        try:
            assert s.get("cube/should-not-exist") is None
        finally:
            s.close()


def test_writes_are_refused_from_other_sites():
    with _Server() as srv:
        body = {"action": "new", "content": "should not exist"}
        assert srv.post(body, origin="https://evil.example")[0] == 403
        assert srv.post(body, host="evil.example")[0] == 403


def test_writes_are_refused_until_unlocked():
    with _Server() as srv:
        body = {"action": "new", "content": "should not exist"}
        assert srv.post(body, key="")[0] == 401
        assert srv.post(body, key="guess")[0] == 401
        assert srv.unlock("wrong password")[0] == 403
        assert srv.unlock(PASSWORD, token="wrong")[0] == 403
        assert srv.unlock(PASSWORD, origin="https://evil.example")[0] == 403


def test_locking_or_going_idle_ends_editing():
    import kg_serve
    body = {"action": "fill", "cube_id": "cube/nope", "lens": "FACT", "content": "x"}
    with _Server() as srv:
        assert srv.post(body)[0] == 400
        assert srv.request("/api/lock", {}, key=srv.key)[0] == 200
        assert srv.post(body)[0] == 401
    idle, kg_serve.IDLE_SECONDS = kg_serve.IDLE_SECONDS, -1
    try:
        with _Server() as srv:
            assert srv.post(body)[0] == 401
    finally:
        kg_serve.IDLE_SECONDS = idle


def test_the_password_never_reaches_the_page_or_the_file():
    from kg_lock import make_lock, matches
    lock = make_lock(PASSWORD)
    assert PASSWORD not in json.dumps(lock)
    assert matches(PASSWORD, lock) and not matches("wrong password", lock)
    try:
        make_lock("short")
        assert False, "short passwords are refused"
    except ValueError:
        pass
    with _Server() as srv:
        assert srv.key not in srv.page()[1]


def test_lock_file_round_trip():
    import tempfile
    from pathlib import Path
    from kg_lock import load_lock, make_lock, save_lock
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "new" / "lock.json"
        assert load_lock(path) is None
        lock = make_lock(PASSWORD)
        save_lock(lock, path)
        assert load_lock(path) == lock


def test_a_validation_can_be_rewritten():
    with _Server() as srv:
        faces = {lens: "text" for lens in ("FACT", "COUNTER")}
        cid = srv.post({"action": "new", "content": "A claim to validate twice", "faces": faces})[1]["result"]["cube_id"]
        assert srv.post({"action": "fill", "cube_id": cid, "lens": "OPINION", "content": "mine"})[0] == 200
        assert srv.post({"action": "validate", "cube_id": cid, "note": "first"})[0] == 200
        status, reply = srv.post({"action": "validate", "cube_id": cid, "note": "second"})
        assert status == 200, reply
        assert next(c for c in reply["cubes"] if c["id"] == cid)["validation"]["note"] == "second"


def test_a_new_cube_gets_drafts_and_the_page_hears_about_them():
    with _Server() as srv:
        before = srv.request("/api/status", {})[1]["pending"]
        status, reply = srv.post({"action": "new", "content": "A blank cube for the drafter"})
        assert status == 200, reply
        cid = reply["result"]["cube_id"]
        srv.server.drafter.jobs.join()
        status, heard = srv.request("/api/status", {"seen": before})
        assert status == 200 and heard["pending"] == before + 1, heard
        cube = next(c for c in heard["cubes"] if c["id"] == cid)
        assert cube["faces"]["FACT"]["pending"] and cube["faces"]["FACT"]["drafted_by"] == "test"
        assert cube["score"] == 0.0
        assert "cubes" not in srv.request("/api/status", {"seen": before + 1})[1]


def test_phone_and_pc_stay_unlocked_together():
    body = {"action": "fill", "cube_id": "cube/nope", "lens": "FACT", "content": "x"}
    with _Server() as srv:
        phone = srv.unlock(PASSWORD)[1]["key"]
        assert srv.post(body)[0] == 400 and srv.post(body, key=phone)[0] == 400
        srv.request("/api/lock", {}, key=phone)
        assert srv.post(body, key=phone)[0] == 401
        assert srv.post(body)[0] == 400


def test_the_page_is_compressed_for_the_phone():
    import gzip
    with _Server() as srv:
        conn = http.client.HTTPConnection("127.0.0.1", srv.port)
        conn.request("GET", "/", headers={"Accept-Encoding": "gzip, deflate, br"})
        res = conn.getresponse()
        raw = res.read()
        assert res.status == 200 and res.getheader("Content-Encoding") == "gzip"
        page = gzip.decompress(raw).decode("utf-8")
        assert srv.server.token in page and len(raw) < len(page.encode("utf-8")) / 2


def test_a_stalled_phone_does_not_block_the_pc():
    import socket
    with _Server() as srv:
        stalled = socket.create_connection(("127.0.0.1", srv.port))
        stalled.sendall(b"GET / HTTP/1.1\r\n")
        try:
            assert srv.page()[0] == 200
        finally:
            stalled.close()


def test_a_suggested_link_can_be_accepted_from_the_page():
    from kg_agent import propose_neighbour
    with _Server() as srv:
        made = [srv.post({"action": "new", "content": f"Link serve {i}"})[1]["result"]["cube_id"] for i in (1, 2)]
        s = Substrate()
        try:
            pid = propose_neighbour(s, made[0], made[1], "model-draft:test", rationale="test")["proposal_id"]
        finally:
            s.close()
        assert srv.post({"action": "accept", "proposal_id": pid}, key="")[0] == 401
        assert srv.post({"action": "accept", "proposal_id": pid, "word": "sort of"})[0] == 400
        status, reply = srv.post({"action": "accept", "proposal_id": pid, "word": "limits", "reverse": True})
        assert status == 200, reply
        cube = next(c for c in reply["cubes"] if c["id"] == made[0])
        assert made[1] in cube["neighbours"] and cube["link_drafts"] == []
        # The reason and the connecting word stay, so the page can say why they are linked
        assert cube["link_reasons"] == {made[1]: "test"}
        assert cube["link_words"] == {made[1]: {"word": "limits", "from": made[1]}}


def test_a_named_host_is_let_in_and_others_are_not():
    body = {"action": "fill", "cube_id": "cube/nope", "lens": "FACT", "content": "x"}
    name = "pc.tailnet.ts.net"
    with _Server(hosts=[name]) as srv:
        assert srv.post(body, host=name, origin=f"https://{name}")[0] == 400
        assert srv.post(body, host="evil.example")[0] == 403
        assert srv.post(body, host=name, origin="https://evil.example")[0] == 403


def test_an_overlap_can_be_confirmed_only_when_unlocked():
    with _Server() as srv:
        made = [srv.post({"action": "new", "content": f"Overlap serve {i}"})[1]["result"]["cube_id"] for i in (1, 2)]
        body = {"action": "overlap", "a": made[0], "b": made[1], "verdict": "confirmed"}
        assert srv.post(body, key="")[0] == 401
        assert srv.post(body)[0] == 200


def test_asking_for_drafts_needs_the_password():
    with _Server() as srv:
        assert srv.post({"action": "draft"}, key="")[0] == 401
        assert srv.request("/api/status", {}, token=False)[0] == 403
        status, reply = srv.post({"action": "draft"})
        assert status == 200 and "queued" in reply["result"], reply


def test_new_cube_returns_fresh_clusters():
    with _Server() as srv:
        status, reply = srv.post({"action": "new", "content": "Servo current spikes at stall",
                                  "tags": ["Servo"],
                                  "faces": {"COUNTER": "datasheet stall current is a guess"}})
        assert status == 200, reply
        cid = reply["result"]["cube_id"]
        cube = next(c for c in reply["cubes"] if c["id"] == cid)
        assert cube["tags"] == ["servo"] and cube["faces"]["COUNTER"]["filled_by"] == "human"
        assert any(cid in g["members"] for g in reply["modes"]["ALL"]["clusters"])


def test_filling_a_face_replaces_its_draft():
    with _Server() as srv:
        cid = srv.post({"action": "new", "content": "A claim with a drafted view"})[1]["result"]["cube_id"]
        srv.server.drafter.jobs.join()
        status, reply = srv.post({"action": "fill", "cube_id": cid, "lens": "OPINION", "content": "my own words"})
        assert status == 200, reply
        cube = next(c for c in reply["cubes"] if c["id"] == cid)
        assert cube["faces"]["OPINION"]["content"] == "my own words"
        assert "pending" not in cube["faces"]["OPINION"]


def test_accept_validate_and_attest_flow_through_the_rules():
    with _Server() as srv:
        faces = {lens: "text" for lens in ("FACT", "COUNTER", "FICTION", "CONTEXT")}
        status, reply = srv.post({"action": "new", "content": "A claim to walk through", "faces": faces})
        cid = reply["result"]["cube_id"]
        assert srv.post({"action": "attest", "cube_id": cid})[0] == 400
        from kg_agent import propose_face
        s = Substrate()
        try:
            proposal = propose_face(s, cid, "OPINION", "a suggested view", "test")
        finally:
            s.close()
        assert srv.post({"action": "accept", "proposal_id": proposal["proposal_id"]})[0] == 200
        assert srv.post({"action": "validate", "cube_id": cid, "note": "holds"})[0] == 200
        status, reply = srv.post({"action": "attest", "cube_id": cid})
        assert status == 200, reply
        assert next(c for c in reply["cubes"] if c["id"] == cid)["status"] == "attested"


def test_bad_input_is_refused_cleanly():
    with _Server() as srv:
        assert srv.post({"action": "nope"})[0] == 400
        assert srv.post({"action": "new", "content": "  "})[0] == 400
        assert srv.post({"action": "fill", "cube_id": "cube/x", "lens": "NOPE", "content": "y"})[0] == 400


def test_the_build_check_needs_no_unlock_but_saving_does():
    with _Server() as srv:
        status, reply = srv.request("/api/spec", {"name": "Desk Arm", "uses": "tof, camera"})
        assert status == 200 and reply["entity"] == "project/desk-arm", reply
        assert [u["term"] for u in reply["unknown"]] == ["camera"]
        assert srv.request("/api/spec", {"name": "Desk Arm"}, token=False)[0] == 403
        body = {"action": "build", "name": "Desk Arm", "parts": [{"term": "tof", "ids": ["subject/vl53l0x"]}]}
        assert srv.post(body, key="")[0] == 401
        status, reply = srv.post(body)
        assert status == 200 and reply["result"]["entity"] == "project/desk-arm", reply
        _, page = srv.page()
        assert 'id="tobuild"' in page and "cubeEdit.post" in page


if __name__ == "__main__":
    run_tests(globals())
