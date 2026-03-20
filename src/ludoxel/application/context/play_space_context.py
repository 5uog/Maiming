# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ...shared.domain.blocks.registry.default_registry import create_default_registry
from ...shared.domain.play_space import PLAY_SPACE_IDS, PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO, normalize_play_space_id
from ..managers.session_manager import SessionManager
from .my_world.session_factory import create_my_world_session
from .othello.session_factory import create_othello_session

@dataclass
class PlaySpaceContext:
    my_world: SessionManager
    othello: SessionManager
    active_space_id: str = PLAY_SPACE_MY_WORLD

    @staticmethod
    def create_default(seed: int = 0) -> "PlaySpaceContext":
        registry = create_default_registry()

        my_world = create_my_world_session(seed=int(seed), block_registry=registry)
        othello = create_othello_session(seed=int(seed), block_registry=registry)

        return PlaySpaceContext(my_world=my_world, othello=othello, active_space_id=PLAY_SPACE_MY_WORLD)

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