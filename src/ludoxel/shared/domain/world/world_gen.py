# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from typing import Dict

from .world_state import WorldState, BlockKey

def generate_flat_world(*, half_extent: int=32, ground_y: int=0, block_id: str="minecraft:grass_block") -> WorldState:
    blocks: Dict[BlockKey, str] = {}
    e = int(max(1, half_extent))
    gy = int(ground_y)

    for x in range(-e, e + 1):
        for z in range(-e, e + 1):
            blocks[(int(x), int(gy), int(z))] = str(block_id)

    return WorldState(blocks=blocks, revision=1)