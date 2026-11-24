"""Typed, versioned settings persisted as JSON."""

from __future__ import annotations

import json
import logging
import secrets
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path

from platformdirs import user_config_dir

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DEFAULT_PORT = 47615


def new_token() -> str:
    return secrets.token_urlsafe(18)


@dataclass(frozen=True, slots=True)
class Settings:
    port: int = DEFAULT_PORT
    token: str = field(default_factory=new_token)
    window_title_pattern: str = r"^Minecraft"
    instance_dir_override: str = ""
    key_delay_ms: int = 5
    menu_wait_ms: int = 500
    startup_delay_ms: int = 500
    focus_settle_ms: int = 300
    step_timeout_s: int = 10
    load_timeout_s: int = 120
    abort_key: str = "f8"
    auto_run: bool = True
    start_in_tray: bool = False


def _coerce(raw: dict[str, object]) -> Settings:
    """Build Settings from untrusted JSON, keeping defaults for missing or mistyped fields."""
    settings = Settings()
    updates: dict[str, object] = {}
    for f in fields(Settings):
        if f.name not in raw:
            continue
        value = raw[f.name]
        default = getattr(settings, f.name)
        # bool is a subclass of int: compare exact types.
        if type(value) is type(default):
            updates[f.name] = value
        else:
            log.warning("Ignoring setting %s with wrong type %s", f.name, type(value).__name__)
    return replace(settings, **updates)  # type: ignore[arg-type]


def _migrate(raw: dict[str, object]) -> dict[str, object]:
    version = raw.get("schema_version", SCHEMA_VERSION)
    # Future schema migrations go here, e.g. `if version == 1: ...; version = 2`.
    if version != SCHEMA_VERSION:
        log.warning("Unknown settings schema %r; using what can be read", version)
    return raw


class ConfigStore:
    def __init__(self, directory: Path | None = None) -> None:
        base = directory or Path(user_config_dir("mcsr-quickstart", appauthor=False))
        self.path = base / "settings.json"

    def load(self) -> Settings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            settings = Settings()
            self.save(settings)
            return settings
        except (OSError, json.JSONDecodeError) as exc:
            log.error("Could not read %s (%s); using defaults", self.path, exc)
            return Settings()
        if not isinstance(raw, dict):
            return Settings()
        return _coerce(_migrate(raw))

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema_version": SCHEMA_VERSION, **asdict(settings)}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)
