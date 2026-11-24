"""Wire protocol between the browser extension and the app (payload version 1).

Mirrors ``LaunchPayload`` in ``extension/src/types.ts``.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import NotRequired, TypedDict

from .seed import SeedRequest, SeedSet, is_valid_seed

PROTOCOL_VERSION = 1


class SeedsJson(TypedDict):
    overworld: str
    nether: str
    rng: NotRequired[str]


class LaunchPayloadJson(TypedDict):
    v: int
    site: str
    seeds: SeedsJson
    sourceUrl: str
    label: NotRequired[str]


class PayloadError(ValueError):
    pass


def _seed(obj: dict[str, object], key: str, *, required: bool) -> str | None:
    value = obj.get(key)
    if value is None:
        if required:
            raise PayloadError(f"missing seed '{key}'")
        return None
    if not isinstance(value, str) or not is_valid_seed(value.strip()):
        raise PayloadError(f"seed '{key}' is not a valid numeric seed")
    return value.strip()


def parse_launch_payload(raw: object, known_sites: Collection[str]) -> SeedRequest:
    """Validate an untrusted JSON payload and turn it into a ``SeedRequest``."""
    if not isinstance(raw, dict):
        raise PayloadError("payload must be an object")
    if raw.get("v") != PROTOCOL_VERSION:
        raise PayloadError(f"unsupported payload version {raw.get('v')!r}")

    site = raw.get("site")
    if not isinstance(site, str):
        raise PayloadError("site must be a string")
    if known_sites and site not in known_sites:
        raise PayloadError(f"unknown site '{site}'")

    seeds = raw.get("seeds")
    if not isinstance(seeds, dict):
        raise PayloadError("seeds must be an object")
    overworld = _seed(seeds, "overworld", required=True)
    nether = _seed(seeds, "nether", required=True)
    rng = _seed(seeds, "rng", required=False)
    assert overworld is not None and nether is not None

    source_url = raw.get("sourceUrl")
    if not isinstance(source_url, str):
        raise PayloadError("sourceUrl must be a string")

    label = raw.get("label")
    if label is not None and not isinstance(label, str):
        raise PayloadError("label must be a string")

    return SeedRequest(
        site=site,
        seeds=SeedSet(overworld=overworld, nether=nether, rng=rng),
        source_url=source_url[:500],
        label=label[:120] if label else None,
    )
