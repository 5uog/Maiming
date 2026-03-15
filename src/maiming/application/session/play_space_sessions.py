# FILE: src/maiming/application/session/play_space_sessions.py
from __future__ import annotations
from dataclasses import dataclass

from ...core.math.vec3 import Vec3
from ..othello.othello_session_factory import create_othello_session
from ...domain.blocks.default_registry import create_default_registry
from ...domain.entities.player_entity import PlayerEntity
from ...domain.play_space import PLAY_SPACE_IDS, PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO, normalize_play_space_id
from ...domain.world.world_gen import generate_test_map
from .session_manager import SessionManager
from .session_settings import SessionSettings

MY_WORLD_SPAWN: tuple[float, float, float] = (0.0, 1.0, -10.0)

def _make_settings(*, seed: int, spawn: tuple[float, float, float]) -> SessionSettings:
    return SessionSettings(seed=int(seed), spawn_x=float(spawn[0]), spawn_y=float(spawn[1]), spawn_z=float(spawn[2]))

def _make_player(*, spawn: tuple[float, float, float], yaw_deg: float = 0.0, pitch_deg: float = 0.0) -> PlayerEntity:
    return PlayerEntity(position=Vec3(float(spawn[0]), float(spawn[1]), float(spawn[2])), velocity=Vec3(0.0, 0.0, 0.0), yaw_deg=float(yaw_deg), pitch_deg=float(pitch_deg))

@dataclass
class PlaySpaceSessions:
    my_world: SessionManager
    othello: SessionManager
    active_space_id: str = PLAY_SPACE_MY_WORLD

    @staticmethod
    def create_default(seed: int = 0) -> "PlaySpaceSessions":
        registry = create_default_registry()

        my_world = SessionManager(settings=_make_settings(seed=int(seed), spawn=MY_WORLD_SPAWN), world=generate_test_map(seed=int(seed)), player=_make_player(spawn=MY_WORLD_SPAWN), block_registry=registry)

        othello = create_othello_session(seed=int(seed), block_registry=registry)

        return PlaySpaceSessions(my_world=my_world, othello=othello, active_space_id=PLAY_SPACE_MY_WORLD)

    def all_sessions(self) -> tuple[SessionManager, ...]:
        return (self.my_world, self.othello)

    def session_for(self, space_id: object) -> SessionManager:
        normalized = normalize_play_space_id(space_id)
        if normalized == PLAY_SPACE_OTHELLO:
            return self.othello
        return self.my_world

    def active_session(self) -> SessionManager:
        return self.session_for(self.active_space_id)

    def set_active_space(self, space_id: object) -> SessionManager:
        normalized = normalize_play_space_id(space_id)
        self.active_space_id = normalized
        return self.session_for(normalized)

    def known_space_ids(self) -> tuple[str, ...]:
        return PLAY_SPACE_IDS