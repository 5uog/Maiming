# FILE: tests/test_app_state_store.py
from __future__ import annotations
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.domain.othello.types import OTHELLO_TIME_CONTROL_NONE, SIDE_WHITE, OthelloGameState, OthelloSettings
from maiming.domain.play_space import PLAY_SPACE_OTHELLO
from maiming.infrastructure.persistence.app_state_store import AppState, AppStateStore, PersistedInventory, PersistedOthelloSpace, PersistedPlaySpace, PersistedPlayer, PersistedSettings, PersistedWorld


class AppStateStoreTests(unittest.TestCase):
    def _make_root(self) -> Path:
        root = ROOT / "tests" / f"_state_store_{uuid.uuid4().hex}"
        user_data = root / "user_data"
        user_data.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_load_migrates_legacy_single_world_payload(self) -> None:
        root = self._make_root()
        user_data = root / "user_data"

        (user_data / "player_state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "settings": {"creative_mode": True, "render_distance_chunks": 8},
                    "inventory": {
                        "creative_hotbar_slots": ["minecraft:stone"] * 9,
                        "creative_selected_hotbar_index": 2,
                    },
                }
            ),
            encoding="utf-8",
        )
        (user_data / "world_state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "player": {"pos": [1.0, 2.0, 3.0], "vel": [0.0, 0.0, 0.0]},
                    "world": {"revision": 3, "blocks": [[0, 0, 0, "minecraft:grass_block"]]},
                }
            ),
            encoding="utf-8",
        )

        state = AppStateStore(project_root=root).load()
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(2, state.inventory.creative_selected_hotbar_index)
        self.assertEqual(3, state.my_world.world.revision)
        self.assertEqual("minecraft:grass_block", state.my_world.world.blocks[(0, 0, 0)])
        self.assertEqual("othello:start", state.inventory.othello_hotbar_slots[0])
        self.assertEqual("othello:settings", state.inventory.othello_hotbar_slots[8])

    def test_save_and_load_round_trip_multi_space_payload(self) -> None:
        root = self._make_root()
        store = AppStateStore(project_root=root)
        state = AppState(
            current_space_id=PLAY_SPACE_OTHELLO,
            settings=PersistedSettings(creative_mode=True),
            inventory=PersistedInventory(
                creative_hotbar_slots=("minecraft:stone",) * 9,
                creative_selected_hotbar_index=1,
                survival_hotbar_slots=("",) * 9,
                survival_selected_hotbar_index=0,
                othello_hotbar_slots=("othello:start", "", "", "", "", "", "", "", "othello:settings"),
                othello_selected_hotbar_index=8,
            ),
            othello_settings=OthelloSettings(time_control=OTHELLO_TIME_CONTROL_NONE, player_side=SIDE_WHITE),
            my_world=PersistedPlaySpace(
                player=PersistedPlayer(pos_x=4.0, pos_y=5.0, pos_z=6.0),
                world=PersistedWorld(revision=2, blocks={(1, 0, 1): "minecraft:stone"}),
            ),
            othello_space=PersistedOthelloSpace(
                player=PersistedPlayer(pos_x=7.0, pos_y=8.0, pos_z=9.0),
                world=PersistedWorld(revision=4, blocks={(0, 0, 0): "minecraft:grass_block"}),
                othello_game_state=OthelloGameState(settings=OthelloSettings(time_control=OTHELLO_TIME_CONTROL_NONE, player_side=SIDE_WHITE)),
            ),
        )
        store.save(state)
        loaded = store.load()
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(PLAY_SPACE_OTHELLO, loaded.current_space_id)
        self.assertEqual(8, loaded.inventory.othello_selected_hotbar_index)
        self.assertEqual(SIDE_WHITE, loaded.othello_settings.player_side)
        self.assertEqual(4, loaded.othello_space.world.revision)
        self.assertEqual((7.0, 8.0, 9.0), (loaded.othello_space.player.pos_x, loaded.othello_space.player.pos_y, loaded.othello_space.player.pos_z))


if __name__ == "__main__":
    unittest.main()
