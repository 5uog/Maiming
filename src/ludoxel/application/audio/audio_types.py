# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

SELECTION_RANDOM = "random"
SELECTION_ROUND_ROBIN = "round_robin"

DEFAULT_SPATIAL_DISTANCE_CUTOFF = 16.0
DEFAULT_SPATIAL_SIZE = 0.75

@dataclass(frozen=True)
class AudioSamplePool:
    relative_paths: tuple[str, ...]
    category: str
    selection_mode: str
    spatial: bool = True
    distance_cutoff: float = DEFAULT_SPATIAL_DISTANCE_CUTOFF
    size: float = DEFAULT_SPATIAL_SIZE
    max_polyphony: int = 4
    cooldown_s: float = 0.0

def make_audio_pool(*paths: str, category: str, selection_mode: str = SELECTION_RANDOM, spatial: bool = True, distance_cutoff: float = DEFAULT_SPATIAL_DISTANCE_CUTOFF, size: float = DEFAULT_SPATIAL_SIZE, max_polyphony: int = 4, cooldown_s: float = 0.0) -> AudioSamplePool:
    return AudioSamplePool(relative_paths=tuple(str(path) for path in paths), category=str(category), selection_mode=str(selection_mode), spatial=bool(spatial), distance_cutoff=float(distance_cutoff), size=float(size), max_polyphony=int(max(1, int(max_polyphony))), cooldown_s=max(0.0, float(cooldown_s)))

def indexed_paths(prefix: str, stem: str, count: int, *, ext: str = "wav", start: int = 1) -> tuple[str, ...]:
    root = str(prefix).rstrip("/")
    base = str(stem).strip()
    total = int(max(0, int(count)))
    begin = int(start)
    return tuple(f"{root}/{base}{index}.{ext}" for index in range(begin, begin + total))