# FILE: src/maiming/domain/world/world_gen.py
from __future__ import annotations
from typing import Dict

from .world_state import WorldState, BlockKey

OTHELLO_BOARD_SIZE: int = 8
OTHELLO_BOARD_MIN_X: int = -(OTHELLO_BOARD_SIZE // 2)
OTHELLO_BOARD_MIN_Z: int = -(OTHELLO_BOARD_SIZE // 2)
OTHELLO_DEFAULT_GROUND_Y: int = 0
OTHELLO_GRASS_TOP_Y: float = float(OTHELLO_DEFAULT_GROUND_Y + 1)
OTHELLO_BOARD_BLOCK_Y: int = OTHELLO_DEFAULT_GROUND_Y + 1
OTHELLO_BOARD_SURFACE_Y: float = float(OTHELLO_BOARD_BLOCK_Y + 1)
OTHELLO_BOARD_DARK_BLOCK_ID: str = "minecraft:dark_oak_planks"
OTHELLO_BOARD_LIGHT_BLOCK_ID: str = "minecraft:spruce_planks"

def generate_flat_world(*, half_extent: int = 32, ground_y: int = 0, block_id: str = "minecraft:grass_block") -> WorldState:
    blocks: Dict[BlockKey, str] = {}
    e = int(max(1, half_extent))
    gy = int(ground_y)

    for x in range(-e, e + 1):
        for z in range(-e, e + 1):
            blocks[(int(x), int(gy), int(z))] = str(block_id)

    return WorldState(blocks=blocks, revision=1)

def generate_test_map(seed: int = 0, params=None) -> WorldState:
    _ = int(seed)
    _ = params
    return generate_flat_world()

def othello_board_block_updates(*, board_y: int = OTHELLO_BOARD_BLOCK_Y) -> Dict[BlockKey, str]:
    updates: Dict[BlockKey, str] = {}
    by = int(board_y)

    for row in range(OTHELLO_BOARD_SIZE):
        for col in range(OTHELLO_BOARD_SIZE):
            x = int(OTHELLO_BOARD_MIN_X + col)
            z = int(OTHELLO_BOARD_MIN_Z + row)
            block_id = OTHELLO_BOARD_DARK_BLOCK_ID if ((row + col) % 2 == 0) else OTHELLO_BOARD_LIGHT_BLOCK_ID
            updates[(x, by, z)] = str(block_id)

    return updates

def ensure_othello_board_layout(world: WorldState, *, board_y: int = OTHELLO_BOARD_BLOCK_Y) -> None:
    world.set_blocks_bulk(updates=othello_board_block_updates(board_y=int(board_y)))

def is_othello_board_footprint(x: float, z: float) -> bool:
    xf = float(x)
    zf = float(z)
    return bool(float(OTHELLO_BOARD_MIN_X) <= xf < float(OTHELLO_BOARD_MIN_X + OTHELLO_BOARD_SIZE) and float(OTHELLO_BOARD_MIN_Z) <= zf < float(OTHELLO_BOARD_MIN_Z + OTHELLO_BOARD_SIZE))

def generate_othello_world(*, half_extent: int = 48, ground_y: int = 0) -> WorldState:
    world = generate_flat_world(half_extent=int(max(16, half_extent)), ground_y=int(ground_y), block_id="minecraft:grass_block")
    ensure_othello_board_layout(world, board_y=int(ground_y) + 1)
    return world