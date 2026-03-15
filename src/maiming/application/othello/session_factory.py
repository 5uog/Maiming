# FILE: src/maiming/application/othello/session_factory.py
from __future__ import annotations
from dataclasses import dataclass

from ...core.math.vec3 import Vec3
from ...domain.blocks.block_registry import BlockRegistry
from ...domain.entities.player_entity import PlayerEntity
from ...domain.othello.board import ensure_othello_board_layout
from ...domain.world.world_gen import generate_flat_world
from ...domain.world.world_state import WorldState
from ..session.session_manager import SessionManager
from ..session.session_settings import SessionSettings

OTHELLO_SPAWN: tuple[float, float, float] = (0.0, 1.0, -12.0)
OTHELLO_YAW_DEG: float = 0.0
OTHELLO_PITCH_DEG: float = 0.0

@dataclass(frozen=True)
class OthelloSessionSeed:
    seed: int = 0
    spawn: tuple[float, float, float] = OTHELLO_SPAWN
    yaw_deg: float = OTHELLO_YAW_DEG
    pitch_deg: float = OTHELLO_PITCH_DEG

def _make_settings(*, spec: OthelloSessionSeed) -> SessionSettings:
    spawn = tuple(spec.spawn)
    return SessionSettings(seed=int(spec.seed), spawn_x=float(spawn[0]), spawn_y=float(spawn[1]), spawn_z=float(spawn[2]))

def _make_player(*, spec: OthelloSessionSeed) -> PlayerEntity:
    spawn = tuple(spec.spawn)
    return PlayerEntity(position=Vec3(float(spawn[0]), float(spawn[1]), float(spawn[2])), velocity=Vec3(0.0, 0.0, 0.0), yaw_deg=float(spec.yaw_deg), pitch_deg=float(spec.pitch_deg))

def _make_world() -> WorldState:
    world = generate_flat_world(half_extent=48, ground_y=0, block_id="minecraft:grass_block")
    ensure_othello_board_layout(world)
    return world

def create_othello_session(*, seed: int = 0, block_registry: BlockRegistry) -> SessionManager:
    spec = OthelloSessionSeed(seed=int(seed))
    return SessionManager(settings=_make_settings(spec=spec), world=_make_world(), player=_make_player(spec=spec), block_registry=block_registry)