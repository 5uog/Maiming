# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .app_state_schema import AppState, PersistedOthelloSpace, PersistedPlaySpace, PlayerStateFile, WorldStateFile
from .json_file_store import JsonFileStore

@dataclass
class AppStateStore:
    project_root: Path

    def _player_store(self) -> JsonFileStore:
        path = Path(self.project_root) / "configs" / "player_state.json"
        return JsonFileStore(path=path)

    def _world_store(self) -> JsonFileStore:
        path = Path(self.project_root) / "configs" / "world_state.json"
        return JsonFileStore(path=path)

    def load(self) -> AppState | None:
        raw_player = self._player_store().read()
        raw_world = self._world_store().read()

        if raw_player is None and raw_world is None:
            return None

        player_file = PlayerStateFile.from_dict(raw_player or {})
        world_file = WorldStateFile.from_dict(raw_world or {})

        return AppState(current_space_id=player_file.current_space_id, settings=player_file.settings, inventory=player_file.inventory, othello_settings=player_file.othello_settings.normalized(), my_world=world_file.my_world, othello_space=world_file.othello_space)

    def save(self, state: AppState) -> None:
        player_file = PlayerStateFile(version=5, current_space_id=state.current_space_id, settings=state.settings, inventory=state.inventory, othello_settings=state.othello_settings.normalized())
        world_file = WorldStateFile(version=2, my_world=state.my_world if isinstance(state.my_world, PersistedPlaySpace) else PersistedPlaySpace(), othello_space=(state.othello_space if isinstance(state.othello_space, PersistedOthelloSpace) else PersistedOthelloSpace()))

        self._player_store().write(player_file.to_dict())
        self._world_store().write(world_file.to_dict())