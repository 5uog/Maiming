# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/context/runtime/audio_preferences.py
from __future__ import annotations

from dataclasses import dataclass

AUDIO_CATEGORY_MASTER = "master"
AUDIO_CATEGORY_AMBIENT = "ambient"
AUDIO_CATEGORY_BLOCK = "block"
AUDIO_CATEGORY_PLAYER = "player"

AUDIO_CATEGORY_ORDER: tuple[str, ...] = (AUDIO_CATEGORY_MASTER, AUDIO_CATEGORY_AMBIENT, AUDIO_CATEGORY_BLOCK, AUDIO_CATEGORY_PLAYER)


def _clamp_volume(value: object, *, default: float = 1.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        numeric = float(default)
    return float(max(0.0, min(1.0, numeric)))


@dataclass(frozen=True)
class AudioPreferences:
    master: float = 1.0
    ambient: float = 1.0
    block: float = 1.0
    player: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "master", _clamp_volume(self.master))
        object.__setattr__(self, "ambient", _clamp_volume(self.ambient))
        object.__setattr__(self, "block", _clamp_volume(self.block))
        object.__setattr__(self, "player", _clamp_volume(self.player))

    def normalized(self) -> "AudioPreferences":
        return self

    def volume_for(self, category: str) -> float:
        key = str(category).strip().lower()
        if key == AUDIO_CATEGORY_AMBIENT:
            return float(self.master) * float(self.ambient)
        if key == AUDIO_CATEGORY_BLOCK:
            return float(self.master) * float(self.block)
        if key == AUDIO_CATEGORY_PLAYER:
            return float(self.master) * float(self.player)
        return float(self.master)

    def to_dict(self) -> dict[str, float]:
        return {AUDIO_CATEGORY_MASTER: float(self.master), AUDIO_CATEGORY_AMBIENT: float(self.ambient), AUDIO_CATEGORY_BLOCK: float(self.block), AUDIO_CATEGORY_PLAYER: float(self.player)}

    @staticmethod
    def from_dict(data: object) -> "AudioPreferences":
        if not isinstance(data, dict):
            return AudioPreferences()
        return AudioPreferences(master=_clamp_volume(data.get(AUDIO_CATEGORY_MASTER, 1.0)), ambient=_clamp_volume(data.get(AUDIO_CATEGORY_AMBIENT, 1.0)), block=_clamp_volume(data.get(AUDIO_CATEGORY_BLOCK, 1.0)), player=_clamp_volume(data.get(AUDIO_CATEGORY_PLAYER, 1.0)))
