"""Work on cubes in the browser. A small server on this machine only.

A web page cannot write to sc.db, so this serves the page and applies what you
do there through the same kg_agent functions the CLI uses. Other sites in your
browser can reach localhost, so every request needs the token issued with the
page, and requests naming another host or origin are refused. Writes also need
the key handed out for the editing password, which lapses when left idle.
"""
import gzip
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from store.substrate import Substrate

from kg_agent import (CONNECTING_WORDS, LENSES, accept_proposal, attest, create_cube, fill_face,
                      list_proposals, reject_proposal, validate)
from kg_build import alias as build_alias, check as build_check, save as build_save
from kg_fill import Drafter, cubes_with_blanks, draft_cube, pending_drafts
from kg_lens_links import all_modes
from kg_lock import matches
from kg_overlaps import decide
from kg_view import collect, hubs, render, things, user_name


# Room for a CSV import; every other field is held to MAX_TEXT
MAX_BODY = 1024 * 1024
MAX_TEXT = 5000
IDLE_SECONDS = 30 * 60
# A phone on a slow relay must not hold a request open for ever
SOCKET_SECONDS = 60


def _same(sent, expected):
    return secrets.compare_digest(sent.encode("utf-8"), expected.encode("utf-8"))


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
    words = [w for w in data.get("words", []) if isinstance(w, str) and w.strip()]
    if words:
        from kg_claim_links import set_words
        set_words(s, result["cube_id"], add=words[:12], by=by)
    return result


def _import(s, data, by):
    """A CSV of claims: what it would make, or, with write set, make it."""
    from kg_csv import preview, summary, write
    text = data.get("csv")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("csv is required")
    if data.get("write") is True:
        made = write(s, text, by)
        return {"made": made if isinstance(made, str) else summary(made)}
    lines, problems = preview(s, text)
    return {"plan": lines, "problems": problems}


def _proposal(s, data, by, act):
    pid = _text(data, "proposal_id")
    if act == "accept":
        word = _text(data, "word", required=False) or None
        return accept_proposal(s, pid, accepted_by=by, word=word, reverse=data.get("reverse") is True)
    return reject_proposal(s, pid, rejected_by=by, reason=_text(data, "reason", required=False) or None)


ACTIONS = {
    "fill": _fill,
    "new": _new,
    "accept": lambda s, d, by: _proposal(s, d, by, "accept"),
    "reject": lambda s, d, by: _proposal(s, d, by, "reject"),
    "validate": lambda s, d, by: validate(s, _text(d, "cube_id"), by, note=_text(d, "note")),
    "attest": lambda s, d, by: attest(s, _text(d, "cube_id"), by),
    "overlap": lambda s, d, by: decide(s, _text(d, "a"), _text(d, "b"), _text(d, "verdict"), by),
    "import": _import,
    "build": lambda s, d, by: build_save(s, d, by),
    "alias": lambda s, d, by: build_alias(s, d, by),
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


def make_handler(by, token, port, lock, drafter, writing, hosts=()):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}", *hosts}
    sessions = {}
    guessing = threading.Lock()

    def unlocked(sent):
        """Each device unlocks on its own, so the phone does not lock the PC."""
        if time.time() > sessions.get(sent, 0):
            sessions.pop(sent, None)
            return False
        sessions[sent] = time.time() + IDLE_SECONDS
        return True

    class Handler(BaseHTTPRequestHandler):
        timeout = SOCKET_SECONDS

        def log_message(self, *args):
            pass

        def _send(self, code, body, kind="application/json"):
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            # The page is large, and the phone may reach it through a relay
            if "gzip" in self.headers.get("Accept-Encoding", ""):
                raw = gzip.compress(raw, 6)
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _json(self, code, value):
            self._send(code, json.dumps(value, ensure_ascii=False))

        def _host_ok(self):
            return self.headers.get("Host") in allowed_hosts

        def _unlock(self, data):
            password = data.get("password")
            # One try at a time, so the pause also slows guessing
            with guessing:
                if not isinstance(password, str) or not matches(password, lock):
                    time.sleep(1)
                    return self._json(403, {"error": "wrong password"})
            key = secrets.token_urlsafe(24)
            sessions[key] = time.time() + IDLE_SECONDS
            return self._json(200, {"key": key})

        def _act(self, s, data):
            if data.get("action") == "draft":
                waiting = cubes_with_blanks(s)
                for cube_id in waiting:
                    drafter.add(cube_id)
                return {"queued": len(waiting)}
            result = apply_action(s, data, by)
            if data.get("action") == "new" and "cube_id" in result:
                drafter.add(result["cube_id"])
            return result

        def _status(self, data):
            """How many drafts wait. Sends the cubes too if that number has moved."""
            s = Substrate()
            try:
                pending = pending_drafts(s)
                reply = {"pending": pending, "drafting": drafter.waiting(), "error": drafter.error}
                if data.get("seen") not in (None, pending):
                    reply.update(state(s))
                return self._json(200, reply)
            finally:
                s.close()

        def _spec(self, data):
            """The Build panel's check. Read-only, so it needs no unlock."""
            s = Substrate()
            try:
                picked = data.get("picked") if isinstance(data.get("picked"), dict) else {}
                return self._json(200, build_check(s, _text(data, "name"), _text(data, "uses", required=False),
                                                   {str(k): [i for i in v if isinstance(i, str)]
                                                    for k, v in picked.items() if isinstance(v, list)}))
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            finally:
                s.close()

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "wrong host"})
            if urlsplit(self.path).path != "/":
                return self._json(404, {"error": "not found"})
            s = Substrate()
            try:
                page = render(collect(s), api={"token": token, "by": by, "words": CONNECTING_WORDS},
                              user=user_name(s), hubs=hubs(s), things=things(s))
            finally:
                s.close()
            self._send(200, page, "text/html")

        def do_POST(self):
            origin = self.headers.get("Origin")
            if not self._host_ok() or (origin and urlsplit(origin).netloc not in allowed_hosts):
                return self._json(403, {"error": "wrong origin"})
            if not _same(self.headers.get("X-Cube-Token", ""), token):
                return self._json(403, {"error": "bad token"})
            if self.path not in ("/api/do", "/api/unlock", "/api/lock", "/api/status", "/api/spec"):
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
            if self.path == "/api/unlock":
                return self._unlock(data)
            if self.path == "/api/lock":
                sessions.pop(self.headers.get("X-Cube-Key", ""), None)
                return self._json(200, {"locked": True})
            if self.path == "/api/status":
                return self._status(data)
            if self.path == "/api/spec":
                return self._spec(data)
            if not unlocked(self.headers.get("X-Cube-Key", "")):
                return self._json(401, {"error": "locked"})
            s = Substrate()
            try:
                with writing:
                    result = self._act(s, data)
                if "error" in result:
                    return self._json(400, result)
                return self._json(200, {"result": result, **state(s)})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            finally:
                s.close()

    return Handler


def make_server(by, lock, port=8765, draft=draft_cube, hosts=()):
    token = secrets.token_urlsafe(24)
    # Each request opens its own Substrate and writes share one lock, so
    # requests can run side by side and a slow phone does not stall the PC
    server = ThreadingHTTPServer(("127.0.0.1", port), None)
    writing = threading.Lock()
    server.drafter = Drafter(writing, draft)
    server.RequestHandlerClass = make_handler(by, token, server.server_address[1], lock, server.drafter, writing, hosts)
    server.token = token
    return server
