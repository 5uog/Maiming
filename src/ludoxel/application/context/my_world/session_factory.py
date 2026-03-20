# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ....shared.domain.blocks.registry.block_registry import BlockRegistry
from ....features.my_world.domain.world.world_gen import generate_test_map
from ....shared.domain.world.world_state import WorldState
from ...managers.session_manager import SessionManager
from ..session_builders import make_session_manager

MY_WORLD_SPAWN: tuple[float, float, float] = (0.0, 1.0, -10.0)
MY_WORLD_YAW_DEG: float = 0.0
MY_WORLD_PITCH_DEG: float = 0.0

@dataclass(frozen=True)
class MyWorldSessionSeed:
    seed: int = 0
    spawn: tuple[float, float, float] = MY_WORLD_SPAWN
    yaw_deg: float = MY_WORLD_YAW_DEG
    pitch_deg: float = MY_WORLD_PITCH_DEG

def _make_world(seed: int) -> WorldState:
    return generate_test_map(seed=int(seed))

def create_my_world_session(*, seed: int = 0, block_registry: BlockRegistry) -> SessionManager:
    session_seed = MyWorldSessionSeed(seed=int(seed))
    return make_session_manager(seed=int(session_seed.seed), spawn=tuple(session_seed.spawn), yaw_deg=float(session_seed.yaw_deg), pitch_deg=float(session_seed.pitch_deg), world=_make_world(seed=int(session_seed.seed)), block_registry=block_registry)