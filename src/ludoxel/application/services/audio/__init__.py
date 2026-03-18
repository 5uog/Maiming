# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/services/audio/__init__.py
from __future__ import annotations

from .catalog.ambient_audio_catalog import AMBIENT_KEY_MY_WORLD
from .audio_manager import AudioManager
from .catalog.material_audio_catalog import (
    BLOCK_EVENT_BREAK,
    BLOCK_EVENT_INTERACT_CLOSE,
    BLOCK_EVENT_INTERACT_OPEN,
    BLOCK_EVENT_PLACE,
    PLAYER_EVENT_STEP,
)
from .catalog.player_audio_catalog import (
    PLAYER_EVENT_LAND,
    PLAYER_EVENT_LAND_BIG,
    PLAYER_EVENT_LAND_SMALL,
    PLAYER_EVENT_OTHELLO_FLIP,
    PLAYER_EVENT_OTHELLO_PLACE,
)

__all__ = [
    "AMBIENT_KEY_MY_WORLD",
    "AudioManager",
    "BLOCK_EVENT_BREAK",
    "BLOCK_EVENT_INTERACT_CLOSE",
    "BLOCK_EVENT_INTERACT_OPEN",
    "BLOCK_EVENT_PLACE",
    "PLAYER_EVENT_LAND",
    "PLAYER_EVENT_LAND_BIG",
    "PLAYER_EVENT_LAND_SMALL",
    "PLAYER_EVENT_OTHELLO_FLIP",
    "PLAYER_EVENT_OTHELLO_PLACE",
    "PLAYER_EVENT_STEP",
]
