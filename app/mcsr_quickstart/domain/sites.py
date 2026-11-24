"""Supported sites, loaded from the shared ``sites.json`` that the extension also builds from."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SiteInfo:
    id: str
    name: str
    matches: tuple[str, ...]


class SitesError(Exception):
    pass


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("MCSRQ_SITES_JSON")
    if env:
        paths.append(Path(env))
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if isinstance(bundle_dir, str):
        paths.append(Path(bundle_dir) / "shared" / "sites.json")
    # Source checkout: <repo>/app/mcsr_quickstart/domain/sites.py -> <repo>/shared/sites.json
    paths.append(Path(__file__).resolve().parents[3] / "shared" / "sites.json")
    return paths


def parse_sites(raw: object) -> tuple[SiteInfo, ...]:
    if not isinstance(raw, list):
        raise SitesError("sites.json must contain a list")
    sites: list[SiteInfo] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise SitesError("each site must be an object")
        site_id = entry.get("id")
        name = entry.get("name")
        matches = entry.get("matches")
        if not isinstance(site_id, str) or not isinstance(name, str):
            raise SitesError("site id and name must be strings")
        if not isinstance(matches, list) or not all(isinstance(m, str) for m in matches):
            raise SitesError(f"site {site_id!r}: matches must be a list of strings")
        sites.append(SiteInfo(id=site_id, name=name, matches=tuple(matches)))
    return tuple(sites)


def load_sites(path: Path | None = None) -> tuple[SiteInfo, ...]:
    """Load the site list. Returns an empty tuple when no sites.json can be found."""
    candidates = [path] if path is not None else _candidate_paths()
    for candidate in candidates:
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as fh:
                return parse_sites(json.load(fh))
    return ()
