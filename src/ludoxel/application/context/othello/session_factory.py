# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ....shared.domain.blocks.registry.block_registry import BlockRegistry
from ....features.othello.domain.game.board import ensure_othello_board_layout
from ....shared.domain.world.world_gen import generate_flat_world
from ....shared.domain.world.world_state import WorldState
from ...managers.session_manager import SessionManager
from ..session_builders import make_session_manager

OTHELLO_SPAWN: tuple[float, float, float] = (0.0, 1.0, -12.0)
OTHELLO_YAW_DEG: float = 0.0
OTHELLO_PITCH_DEG: float = 0.0

@dataclass(frozen=True)
class OthelloSessionSeed:
    seed: int = 0
    spawn: tuple[float, float, float] = OTHELLO_SPAWN
    yaw_deg: float = OTHELLO_YAW_DEG
    pitch_deg: float = OTHELLO_PITCH_DEG

def _make_world() -> WorldState:
    world = generate_flat_world(half_extent=48, ground_y=0, block_id="minecraft:grass_block")
    ensure_othello_board_layout(world)
    return world

def create_othello_session(*, seed: int = 0, block_registry: BlockRegistry) -> SessionManager:
    spec = OthelloSessionSeed(seed=int(seed))
    return make_session_manager(seed=int(spec.seed), spawn=tuple(spec.spawn), yaw_deg=float(spec.yaw_deg), pitch_deg=float(spec.pitch_deg), world=_make_world(), block_registry=block_registry)