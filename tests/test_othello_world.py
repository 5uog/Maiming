# FILE: tests/test_othello_world.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.domain.world.world_gen import (
    OTHELLO_BOARD_BLOCK_Y,
    OTHELLO_BOARD_DARK_BLOCK_ID,
    OTHELLO_BOARD_LIGHT_BLOCK_ID,
    OTHELLO_BOARD_MIN_X,
    OTHELLO_BOARD_MIN_Z,
    generate_othello_world,
)


class OthelloWorldTests(unittest.TestCase):
    def test_generate_othello_world_builds_raised_checkerboard_platform(self) -> None:
        world = generate_othello_world(half_extent=10, ground_y=0)
        blocks = world.snapshot_blocks()

        self.assertEqual("minecraft:grass_block", blocks[(0, 0, 0)])

        for row in range(8):
            for col in range(8):
                x = OTHELLO_BOARD_MIN_X + col
                z = OTHELLO_BOARD_MIN_Z + row
                expected = OTHELLO_BOARD_DARK_BLOCK_ID if ((row + col) % 2 == 0) else OTHELLO_BOARD_LIGHT_BLOCK_ID
                self.assertEqual(expected, blocks[(x, OTHELLO_BOARD_BLOCK_Y, z)])


if __name__ == "__main__":
    unittest.main()
