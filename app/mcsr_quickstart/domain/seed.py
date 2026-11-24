"""Seed value types shared by every layer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_SEED_RE = re.compile(r"^-?\d{1,20}$")


class SeedField(Enum):
    """Which seed of a seed set a typed step should insert."""

    OVERWORLD = "overworld"
    NETHER = "nether"
    RNG = "rng"


def is_valid_seed(value: str) -> bool:
    """A Minecraft numeric seed: optional minus sign followed by up to 20 digits."""
    return bool(_SEED_RE.match(value))


@dataclass(frozen=True, slots=True)
class SeedSet:
    """The seeds that make up one MCSR Ranked match."""

    overworld: str
    nether: str
    rng: str | None = None

    def get(self, field: SeedField) -> str | None:
        match field:
            case SeedField.OVERWORLD:
                return self.overworld
            case SeedField.NETHER:
                return self.nether
            case SeedField.RNG:
                return self.rng


@dataclass(frozen=True, slots=True)
class SeedRequest:
    """A seed set plus where it came from."""

    site: str
    seeds: SeedSet
    source_url: str
    label: str | None = None
