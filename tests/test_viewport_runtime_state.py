# FILE: tests/test_viewport_runtime_state.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.domain.inventory.special_items import OTHELLO_START_ITEM_ID
from maiming.domain.play_space import PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO
from maiming.presentation.widgets.viewport.viewport_runtime_state import ViewportRuntimeState


class ViewportRuntimeStateTests(unittest.TestCase):
    def test_othello_keeps_view_model_enabled_when_hand_is_not_hidden(self) -> None:
        state = ViewportRuntimeState(current_space_id=PLAY_SPACE_OTHELLO, hide_hand=False)
        self.assertTrue(state.view_model_visible())
        self.assertEqual(OTHELLO_START_ITEM_ID, state.current_item_id())
        self.assertIsNone(state.current_block_id())

    def test_hide_hand_disables_view_model_in_all_spaces(self) -> None:
        self.assertFalse(ViewportRuntimeState(current_space_id=PLAY_SPACE_MY_WORLD, hide_hand=True).view_model_visible())
        self.assertFalse(ViewportRuntimeState(current_space_id=PLAY_SPACE_OTHELLO, hide_hand=True).view_model_visible())


if __name__ == "__main__":
    unittest.main()
