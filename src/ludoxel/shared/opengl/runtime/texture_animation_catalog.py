# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class AnimatedTextureTrack:
    logical_name: str
    frame_sequence: tuple[str, ...]
    frame_duration_s: float

_PRISMARINE_FRAMES: tuple[str, ...] = ("prismarine_rough_01", "prismarine_rough_02", "prismarine_rough_01", "prismarine_rough_03", "prismarine_rough_01", "prismarine_rough_04", "prismarine_rough_02", "prismarine_rough_03", "prismarine_rough_04", "prismarine_rough_03", "prismarine_rough_02", "prismarine_rough_04", "prismarine_rough_02", "prismarine_rough_01", "prismarine_rough_04", "prismarine_rough_01", "prismarine_rough_02", "prismarine_rough_04", "prismarine_rough_03", "prismarine_rough_02", "prismarine_rough_03", "prismarine_rough_04")

_MAGMA_BLOCK_FRAMES: tuple[str, ...] = ("magma_01", "magma_02", "magma_03")

def default_texture_animation_tracks() -> tuple[AnimatedTextureTrack, ...]:
    return (AnimatedTextureTrack(logical_name="magma_01", frame_sequence=_MAGMA_BLOCK_FRAMES, frame_duration_s=0.4), AnimatedTextureTrack(logical_name="prismarine_rough_01", frame_sequence=_PRISMARINE_FRAMES, frame_duration_s=15.0))