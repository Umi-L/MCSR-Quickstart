"""Localhost HTTP bridge for the browser extension.

GET  /status  -> {"ok": true, "version": str, "running": bool}
POST /launch  -> 202 accepted | 400 invalid | 401 bad token | 403 bad origin | 409 busy
"""

from __future__ import annotations

import hmac
import json
import logging
import threading
from collections.abc import Callable, Collection
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

from .. import __version__
from ..domain.protocol import PayloadError, parse_launch_payload
from ..domain.seed import SeedRequest

log = logging.getLogger(__name__)

TOKEN_HEADER = "X-Quickstart-Token"
_ALLOWED_ORIGIN_PREFIXES = ("chrome-extension://", "moz-extension://")
_MAX_BODY = 8 * 1024

LaunchOutcome = Literal["accepted", "busy"]


@dataclass(frozen=True, slots=True)
class ServerHooks:
    token: Callable[[], str]
    known_sites: Callable[[], Collection[str]]
    is_running: Callable[[], bool]
    on_launch: Callable[[SeedRequest], LaunchOutcome]


def _make_handler(hooks: ServerHooks) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"MCSRQuickstart/{__version__}"

        def log_message(self, format: str, *args: object) -> None:
            log.debug("%s - %s", self.address_string(), format % args)

        # -- helpers --------------------------------------------------------------------

        def _send(self, status: int, body: dict[str, object]) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            origin = self.headers.get("Origin")
            if origin and origin.startswith(_ALLOWED_ORIGIN_PREFIXES):
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorised(self) -> bool:
            origin = self.headers.get("Origin")
            if origin is not None and not origin.startswith(_ALLOWED_ORIGIN_PREFIXES):
                self._send(403, {"ok": False, "error": "origin not allowed"})
                return False
            given = self.headers.get(TOKEN_HEADER, "")
            if not hmac.compare_digest(given.encode(), hooks.token().encode()):
                self._send(401, {"ok": False, "error": "bad token"})
                return False
            return True

        # -- verbs ----------------------------------------------------------------------

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            origin = self.headers.get("Origin")
            if origin and origin.startswith(_ALLOWED_ORIGIN_PREFIXES):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST")
                self.send_header("Access-Control-Allow-Headers", f"Content-Type, {TOKEN_HEADER}")
            self.end_headers()

        def do_GET(self) -> None:
            if self.path != "/status":
                self._send(404, {"ok": False, "error": "not found"})
                return
            if self._authorised():
                self._send(200, {"ok": True, "version": __version__, "running": hooks.is_running()})

        def do_POST(self) -> None:
            if self.path != "/launch":
                self._send(404, {"ok": False, "error": "not found"})
                return
            if not self._authorised():
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > _MAX_BODY:
                self._send(400, {"ok": False, "error": "bad body size"})
                return
            try:
                raw = json.loads(self.rfile.read(length))
                request = parse_launch_payload(raw, hooks.known_sites())
            except (json.JSONDecodeError, PayloadError) as exc:
                self._send(400, {"ok": False, "error": str(exc)})
                return
            if hooks.on_launch(request) == "busy":
                self._send(409, {"ok": False, "error": "a run is already in progress"})
                return
            self._send(202, {"ok": True})

    return Handler


class BridgeServer:
    def __init__(self, port: int, hooks: ServerHooks) -> None:
        self._httpd = ThreadingHTTPServer(("127.0.0.1", port), _make_handler(hooks))
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="bridge-server", daemon=True
        )

    @property
    def port(self) -> int:
        return int(self._httpd.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
