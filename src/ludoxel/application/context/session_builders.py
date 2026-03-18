# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/context/session_builders.py
from __future__ import annotations

from ...shared.core.math.vec3 import Vec3
from ...shared.domain.blocks.registry.block_registry import BlockRegistry
from ...shared.domain.entities.player_entity import PlayerEntity
from ...shared.domain.world.world_state import WorldState
from ..managers.session_manager import SessionManager
from .runtime.session_settings import SessionSettings


def make_session_settings(*, seed: int, spawn: tuple[float, float, float]) -> SessionSettings:
    return SessionSettings(
        seed=int(seed),
        spawn_x=float(spawn[0]),
        spawn_y=float(spawn[1]),
        spawn_z=float(spawn[2]),
    )


def make_player_entity(
    *,
    spawn: tuple[float, float, float],
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
) -> PlayerEntity:
    return PlayerEntity(
        position=Vec3(float(spawn[0]), float(spawn[1]), float(spawn[2])),
        velocity=Vec3(0.0, 0.0, 0.0),
        yaw_deg=float(yaw_deg),
        pitch_deg=float(pitch_deg),
    )


def make_session_manager(
    *,
    seed: int,
    spawn: tuple[float, float, float],
    world: WorldState,
    block_registry: BlockRegistry,
    yaw_deg: float = 0.0,
    pitch_deg: float = 0.0,
) -> SessionManager:
    return SessionManager(
        settings=make_session_settings(
            seed=int(seed),
            spawn=tuple(spawn),
        ),
        world=world,
        player=make_player_entity(
            spawn=tuple(spawn),
            yaw_deg=float(yaw_deg),
            pitch_deg=float(pitch_deg),
        ),
        block_registry=block_registry,
    )
