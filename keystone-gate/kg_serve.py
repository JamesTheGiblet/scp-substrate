"""Work on cubes in the browser. A small server on this machine only.

A web page cannot write to sc.db, so this serves the page and applies what you
do there through the same kg_agent functions the CLI uses. Other sites in your
browser can reach localhost, so every write needs the token issued with the
page, and requests naming another host or origin are refused.
"""
import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

from substrate import Substrate

from kg_agent import (LENSES, accept_proposal, attest, create_cube, fill_face,
                      list_proposals, reject_proposal, validate)
from kg_lens_links import all_modes
from kg_view import collect, render


MAX_BODY = 64 * 1024
MAX_TEXT = 5000


def _text(data, key, required=True):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        if required:
            raise ValueError(f"{key} is required")
        return ""
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise ValueError(f"{key} is too long")
    return value


def _fill(s, data, by):
    cube_id, lens = _text(data, "cube_id"), _text(data, "lens")
    result = fill_face(s, cube_id, lens, _text(data, "content"))
    if "error" not in result:
        # Your own words replace any draft waiting on this lens
        for p in list_proposals(s, cube_id=cube_id, status="pending"):
            if p.get("lens") == lens:
                reject_proposal(s, p["id"], rejected_by=by, reason="replaced by hand")
    return {**result, "cube_id": cube_id}


def _new(s, data, by):
    tags = [t.strip().lower() for t in data.get("tags", []) if isinstance(t, str) and t.strip()]
    result = create_cube(s, _text(data, "content"), source=f"written by {by}", tags=tags[:8])
    if "error" in result:
        return result
    faces = data.get("faces") if isinstance(data.get("faces"), dict) else {}
    for lens in LENSES:
        content = _text(faces, lens, required=False)
        if content:
            fill_face(s, result["cube_id"], lens, content)
    return result


def _proposal(s, data, by, act):
    pid = _text(data, "proposal_id")
    if act == "accept":
        return accept_proposal(s, pid, accepted_by=by)
    return reject_proposal(s, pid, rejected_by=by, reason=_text(data, "reason", required=False) or None)


ACTIONS = {
    "fill": _fill,
    "new": _new,
    "accept": lambda s, d, by: _proposal(s, d, by, "accept"),
    "reject": lambda s, d, by: _proposal(s, d, by, "reject"),
    "validate": lambda s, d, by: validate(s, _text(d, "cube_id"), by, note=_text(d, "note")),
    "attest": lambda s, d, by: attest(s, _text(d, "cube_id"), by),
}


def apply_action(s, data, by):
    """Run one action. Returns the result; raises ValueError for bad input."""
    action = ACTIONS.get(data.get("action"))
    if not action:
        raise ValueError("unknown action")
    return action(s, data, by)


def state(s):
    cubes = collect(s)
    return {"cubes": cubes, "modes": all_modes(cubes)}


def make_handler(by, token, port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, kind="application/json"):
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _json(self, code, value):
            self._send(code, json.dumps(value, ensure_ascii=False))

        def _host_ok(self):
            return self.headers.get("Host") in allowed_hosts

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "wrong host"})
            if urlsplit(self.path).path != "/":
                return self._json(404, {"error": "not found"})
            s = Substrate()
            try:
                page = render(collect(s), api={"token": token, "by": by})
            finally:
                s.close()
            self._send(200, page, "text/html")

        def do_POST(self):
            origin = self.headers.get("Origin")
            if not self._host_ok() or (origin and urlsplit(origin).netloc not in allowed_hosts):
                return self._json(403, {"error": "wrong origin"})
            sent = self.headers.get("X-Cube-Token", "")
            if not secrets.compare_digest(sent, token):
                return self._json(403, {"error": "bad token"})
            if self.path != "/api/do":
                return self._json(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json(413, {"error": "too large"})
            try:
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("expected an object")
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            s = Substrate()
            try:
                result = apply_action(s, data, by)
                if "error" in result:
                    return self._json(400, result)
                return self._json(200, {"result": result, **state(s)})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            finally:
                s.close()

    return Handler


def make_server(by, port=8765):
    token = secrets.token_urlsafe(24)
    server = HTTPServer(("127.0.0.1", port), None)
    server.RequestHandlerClass = make_handler(by, token, server.server_address[1])
    server.token = token
    return server
