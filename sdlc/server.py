"""`python3 -m sdlc serve` — local web app over one repository (stdlib only).

Security model: binds to 127.0.0.1, answers only requests whose Host is that loopback
address (blocks DNS rebinding), and accepts writes only as JSON with an X-SDLC header
(a cross-site form cannot set it). Writes are limited to the steps an agent may take
anyway — new, stage, submit. There is no approve endpoint: a gate decision is a person
running `sdlc approve` in a terminal, and an HTTP route would let any local process,
including an agent, record one.
"""

from __future__ import annotations

import json
import mimetypes
import re
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import api, artifacts, gitutil, workitems

APP_DIR = Path(__file__).parent / "webapp"
SITE = Path(__file__).resolve().parent.parent / "web" / "index.html"
WORK_ROUTE = re.compile(r"^/api/work/(W-\d{4,})(?:/(stage|submit))?$")
MAX_BODY = 64 * 1024


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _work_dir(root: Path, work_id: str) -> Path:
    matches = sorted((root / artifacts.WORK_DIR).glob(f"*/{work_id}-*"))
    if len(matches) != 1:
        raise ApiError(HTTPStatus.NOT_FOUND, f"no work item {work_id}")
    return matches[0]


def make_handler(root: Path, allowed_hosts: set[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "sdlc"

        def log_message(self, fmt, *args):  # one short line per request on stderr
            sys.stderr.write(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}\n")

        # -- plumbing -------------------------------------------------------------
        def _send(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: HTTPStatus, data) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def _check_host(self) -> None:
            if (self.headers.get("Host") or "").lower() not in allowed_hosts:
                raise ApiError(HTTPStatus.FORBIDDEN, "unexpected Host header")

        def _body(self) -> dict:
            if self.headers.get("X-SDLC") != "1" or not (self.headers.get("Content-Type") or "").startswith("application/json"):
                raise ApiError(HTTPStatus.FORBIDDEN, "writes need Content-Type: application/json and X-SDLC: 1")
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                raise ApiError(HTTPStatus.BAD_REQUEST, "body is not valid JSON")
            if not isinstance(data, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "body must be a JSON object")
            return data

        def _dispatch(self, fn) -> None:
            try:
                self._check_host()
                fn()
            except ApiError as exc:
                self._json(exc.status, {"error": exc.message})
            except workitems.GateError as exc:
                self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
            except gitutil.GitError as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        # -- routes ---------------------------------------------------------------
        def do_GET(self):
            self._dispatch(self._get)

        def do_POST(self):
            self._dispatch(self._post)

        def _get(self) -> None:
            url = urlparse(self.path)
            path, query = url.path, parse_qs(url.query)
            if path == "/api/overview":
                return self._json(HTTPStatus.OK, api.overview(root))
            if path == "/api/work":
                return self._json(HTTPStatus.OK, api.work_items(root))
            if path == "/api/incidents":
                return self._json(HTTPStatus.OK, api.incidents(root))
            if path == "/api/branch":
                return self._json(HTTPStatus.OK, api.branch_check(root, (query.get("base") or [None])[0]))
            m = WORK_ROUTE.match(path)
            if m and not m.group(2):
                item = api.work_item(root, m.group(1))
                if item is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, f"no work item {m.group(1)}")
                return self._json(HTTPStatus.OK, item)
            if path.startswith("/api/"):
                raise ApiError(HTTPStatus.NOT_FOUND, "no such endpoint")
            self._static(path)

        def _post(self) -> None:
            path = urlparse(self.path).path
            data = self._body()
            if path == "/api/work":
                title = str(data.get("title", "")).strip()
                owner = str(data.get("owner", "")).strip()
                if not title or not owner:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "title and owner are required")
                intent = workitems.new_work(root, title, owner, str(data.get("tier", "T1")))
                return self._json(HTTPStatus.CREATED, {"path": intent.relative_to(root).as_posix(),
                                                       "id": artifacts.load(intent, root).work_id})
            m = WORK_ROUTE.match(path)
            if m and m.group(2):
                stage = str(data.get("stage", ""))
                work = _work_dir(root, m.group(1))
                if m.group(2) == "stage":
                    created = workitems.add_stage(root, work, stage)
                    return self._json(HTTPStatus.CREATED, {"path": created.relative_to(root).as_posix()})
                if stage not in api.STAGES:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "stage must be intent, spec, or plan")
                art = workitems.submit(work / f"{stage}.md", root)
                return self._json(HTTPStatus.OK, {"path": art.rel, "status": art.status})
            raise ApiError(HTTPStatus.NOT_FOUND, "no such endpoint")

        def _static(self, path: str) -> None:
            if path in ("/", "/index.html"):
                target = APP_DIR / "index.html"
            elif path == "/about":
                target = SITE
            else:
                target = (APP_DIR / path.lstrip("/")).resolve()
                if APP_DIR.resolve() not in target.parents:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not found")
            if not target.is_file():
                raise ApiError(HTTPStatus.NOT_FOUND, "not found")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            self._send(HTTPStatus.OK, target.read_bytes(), ctype)

    return Handler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("the sdlc web app only binds to loopback")
    server = ThreadingHTTPServer((host, port), None)
    real_port = server.server_address[1]
    allowed = {f"127.0.0.1:{real_port}", f"localhost:{real_port}", f"[::1]:{real_port}"}
    server.RequestHandlerClass = make_handler(root, allowed)
    return server
