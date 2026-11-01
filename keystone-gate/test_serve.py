"""The browser's way in: writes need the token. Run: python tests/run.py"""
import http.client
import json
import threading

from support_kg import *


class _Server:
    def __enter__(self):
        from kg_serve import make_server
        self.server = make_server("james", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()

    def post(self, data, token=None, host=None, origin=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json", "Host": host or f"127.0.0.1:{self.port}"}
        if token is not False:
            headers["X-Cube-Token"] = token or self.server.token
        if origin:
            headers["Origin"] = origin
        conn.request("POST", "/api/do", json.dumps(data), headers)
        res = conn.getresponse()
        return res.status, json.loads(res.read())

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
        cid = "cube/esp32-logic-is-3v3"
        status, reply = srv.post({"action": "fill", "cube_id": cid, "lens": "COUNTER", "content": "my own words"})
        assert status == 200, reply
        cube = next(c for c in reply["cubes"] if c["id"] == cid)
        assert cube["faces"]["COUNTER"]["content"] == "my own words"
        assert "pending" not in cube["faces"]["COUNTER"]


def test_accept_validate_and_attest_flow_through_the_rules():
    with _Server() as srv:
        cid = "cube/torque-falls-with-arm-length"
        assert srv.post({"action": "attest", "cube_id": cid})[0] == 400
        cube = next(c for c in srv.post({"action": "fill", "cube_id": cid, "lens": "OPINION", "content": "yes"})[1]["cubes"] if c["id"] == cid)
        for lens in ("FACT", "COUNTER", "FICTION", "CONTEXT"):
            assert srv.post({"action": "accept", "proposal_id": cube["faces"][lens]["proposal_id"]})[0] == 200
        assert srv.post({"action": "validate", "cube_id": cid, "note": "holds"})[0] == 200
        status, reply = srv.post({"action": "attest", "cube_id": cid})
        assert status == 200, reply
        assert next(c for c in reply["cubes"] if c["id"] == cid)["status"] == "attested"


def test_bad_input_is_refused_cleanly():
    with _Server() as srv:
        assert srv.post({"action": "nope"})[0] == 400
        assert srv.post({"action": "new", "content": "  "})[0] == 400
        assert srv.post({"action": "fill", "cube_id": "cube/x", "lens": "NOPE", "content": "y"})[0] == 400


if __name__ == "__main__":
    run_tests(globals())
