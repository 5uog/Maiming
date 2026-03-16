# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/play_space.py
from __future__ import annotations

PLAY_SPACE_MY_WORLD: str = "my_world"
PLAY_SPACE_OTHELLO: str = "othello"

PLAY_SPACE_IDS: tuple[str, ...] = (PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO)


def normalize_play_space_id(value: object, *, default: str=PLAY_SPACE_MY_WORLD) -> str:
    raw = str(value).strip().lower()
    if raw in PLAY_SPACE_IDS:
        return raw
    fallback = str(default).strip().lower()
    if fallback in PLAY_SPACE_IDS:
        return fallback
    return PLAY_SPACE_MY_WORLD


def is_othello_space(space_id: object) -> bool:
    return normalize_play_space_id(space_id) == PLAY_SPACE_OTHELLO


def is_my_world_space(space_id: object) -> bool:
    return normalize_play_space_id(space_id) == PLAY_SPACE_MY_WORLD
