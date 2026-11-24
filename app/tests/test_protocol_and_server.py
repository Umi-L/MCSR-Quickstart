from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcsr_quickstart.domain.protocol import PayloadError, parse_launch_payload
from mcsr_quickstart.domain.seed import SeedRequest
from mcsr_quickstart.domain.sites import load_sites
from mcsr_quickstart.infra.config import ConfigStore, Settings
from mcsr_quickstart.infra.server import TOKEN_HEADER, BridgeServer, LaunchOutcome, ServerHooks

VALID: dict[str, Any] = {
    "v": 1,
    "site": "gapcheck",
    "seeds": {"overworld": "-4125175248295031958", "nether": "148780472584739"},
    "sourceUrl": "https://gapcheck.gg/m/1",
}


def test_parse_valid() -> None:
    req = parse_launch_payload(VALID, {"gapcheck"})
    assert req.seeds.overworld == "-4125175248295031958"
    assert req.seeds.rng is None


@pytest.mark.parametrize(
    "mutation",
    [
        {"v": 2},
        {"site": "evil"},
        {"seeds": {"overworld": "12a", "nether": "1"}},
        {"seeds": {"overworld": "1"}},
        {"sourceUrl": 5},
    ],
)
def test_parse_invalid(mutation: dict[str, Any]) -> None:
    with pytest.raises(PayloadError):
        parse_launch_payload({**VALID, **mutation}, {"gapcheck"})


def test_shared_sites_json_loads() -> None:
    ids = {s.id for s in load_sites()}
    assert {"gapcheck", "seedbank"} <= ids


def test_config_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    created = store.load()
    assert store.path.exists()
    store.save(Settings(token=created.token, port=40000))
    assert store.load().port == 40000
    store.path.write_text(json.dumps({"port": "nope", "auto_run": False}))
    loaded = store.load()
    assert loaded.port == Settings().port and loaded.auto_run is False


# -- server -----------------------------------------------------------------------------


class Recorder:
    def __init__(self) -> None:
        self.received: list[SeedRequest] = []
        self.busy = False

    def on_launch(self, request: SeedRequest) -> LaunchOutcome:
        if self.busy:
            return "busy"
        self.received.append(request)
        return "accepted"


@pytest.fixture
def server() -> Iterator[tuple[BridgeServer, Recorder]]:
    rec = Recorder()
    hooks = ServerHooks(
        token=lambda: "secret",
        known_sites=lambda: {"gapcheck"},
        is_running=lambda: rec.busy,
        on_launch=rec.on_launch,
    )
    srv = BridgeServer(0, hooks)
    srv.start()
    yield srv, rec
    srv.stop()


def _post(port: int, body: object, token: str = "secret", origin: str | None = None) -> int:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/launch",
        data=json.dumps(body).encode(),
        headers={TOKEN_HEADER: token, "Content-Type": "application/json",
                 **({"Origin": origin} if origin else {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return exc.code


def test_server_accepts_and_rejects(server: tuple[BridgeServer, Recorder]) -> None:
    srv, rec = server
    assert _post(srv.port, VALID, origin="chrome-extension://abc") == 202
    assert len(rec.received) == 1
    assert _post(srv.port, VALID, token="wrong") == 401
    assert _post(srv.port, VALID, origin="https://evil.example") == 403
    assert _post(srv.port, {**VALID, "v": 9}) == 400
    rec.busy = True
    assert _post(srv.port, VALID) == 409
