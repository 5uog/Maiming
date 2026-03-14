# FILE: tests/test_othello_scene.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.infrastructure.rendering.opengl._internal.scene.othello_scene import (
    OTHELLO_BOARD_TOP_Y,
    OTHELLO_GRASS_TOP_Y,
    OTHELLO_HIGHLIGHT_CENTER_Y,
    OTHELLO_HIGHLIGHT_THICKNESS,
    OTHELLO_PIECE_BOTTOM_Y,
)


class OthelloSceneTests(unittest.TestCase):
    def test_board_and_piece_heights_sit_above_grass_surface(self) -> None:
        self.assertEqual(OTHELLO_GRASS_TOP_Y + 1.0, OTHELLO_BOARD_TOP_Y)
        self.assertGreaterEqual(
            OTHELLO_HIGHLIGHT_CENTER_Y - (OTHELLO_HIGHLIGHT_THICKNESS * 0.5),
            OTHELLO_BOARD_TOP_Y,
        )
        self.assertGreater(OTHELLO_PIECE_BOTTOM_Y, OTHELLO_BOARD_TOP_Y)


if __name__ == "__main__":
    unittest.main()
