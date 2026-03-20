# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import math
from typing import Dict

from .....shared.core.math.vec3 import Vec3
from .....shared.domain.world.world_state import BlockKey, WorldState
from .types import BOARD_CELL_COUNT

BOARD_SIZE: int = int(math.isqrt(int(BOARD_CELL_COUNT)))

OTHELLO_BOARD_MIN_X: int = -(BOARD_SIZE // 2)
OTHELLO_BOARD_MIN_Z: int = -(BOARD_SIZE // 2)
OTHELLO_DEFAULT_GROUND_Y: int = 0
OTHELLO_GRASS_TOP_Y: float = float(OTHELLO_DEFAULT_GROUND_Y + 1)
OTHELLO_BOARD_BLOCK_Y: int = OTHELLO_DEFAULT_GROUND_Y + 1
OTHELLO_BOARD_SURFACE_Y: float = float(OTHELLO_BOARD_BLOCK_Y + 1)
OTHELLO_BOARD_DARK_BLOCK_ID: str = "minecraft:dark_oak_planks"
OTHELLO_BOARD_LIGHT_BLOCK_ID: str = "minecraft:spruce_planks"

def row_col_to_square_index(row: int, col: int) -> int:
    return int(row) * BOARD_SIZE + int(col)

def square_index_to_row_col(square_index: int) -> tuple[int, int]:
    idx = max(0, min(BOARD_CELL_COUNT - 1, int(square_index)))
    return (idx // BOARD_SIZE, idx % BOARD_SIZE)

def row_col_to_world_xz(row: int, col: int) -> tuple[int, int]:
    return (int(OTHELLO_BOARD_MIN_X + int(col)), int(OTHELLO_BOARD_MIN_Z + int(row)))

def square_center(square_index: int) -> tuple[float, float]:
    row, col = square_index_to_row_col(square_index)
    x = float(OTHELLO_BOARD_MIN_X + col) + 0.5
    z = float(OTHELLO_BOARD_MIN_Z + row) + 0.5
    return (float(x), float(z))

def world_xz_to_square_index(x: float, z: float) -> int | None:
    xf = float(x)
    zf = float(z)
    if not is_othello_board_footprint(xf, zf):
        return None
    col = int(math.floor(xf - float(OTHELLO_BOARD_MIN_X)))
    row = int(math.floor(zf - float(OTHELLO_BOARD_MIN_Z)))
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        return None
    return row_col_to_square_index(row, col)

def othello_board_block_updates(*, board_y: int=OTHELLO_BOARD_BLOCK_Y) -> Dict[BlockKey, str]:
    updates: Dict[BlockKey, str] = {}
    board_layer_y = int(board_y)
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            x, z = row_col_to_world_xz(row, col)
            block_id = OTHELLO_BOARD_DARK_BLOCK_ID if ((row + col) % 2 == 0) else OTHELLO_BOARD_LIGHT_BLOCK_ID
            updates[(int(x), int(board_layer_y), int(z))] = str(block_id)
    return updates

def ensure_othello_board_layout(world: WorldState, *, board_y: int=OTHELLO_BOARD_BLOCK_Y) -> None:
    world.set_blocks_bulk(updates=othello_board_block_updates(board_y=int(board_y)))

def is_othello_board_footprint(x: float, z: float) -> bool:
    return bool(float(OTHELLO_BOARD_MIN_X) <= float(x) < float(OTHELLO_BOARD_MIN_X + BOARD_SIZE) and float(OTHELLO_BOARD_MIN_Z) <= float(z) < float(OTHELLO_BOARD_MIN_Z + BOARD_SIZE))

def raycast_board_square(origin: Vec3, direction: Vec3) -> int | None:
    dy = float(direction.y)
    if abs(dy) <= 1e-8:
        return None
    t = (float(OTHELLO_BOARD_SURFACE_Y) - float(origin.y)) / float(dy)
    if t <= 0.0:
        return None
    hit_x = float(origin.x) + float(direction.x) * float(t)
    hit_z = float(origin.z) + float(direction.z) * float(t)
    return world_xz_to_square_index(hit_x, hit_z)