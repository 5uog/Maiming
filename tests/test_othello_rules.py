# FILE: tests/test_othello_rules.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.domain.othello.rules import apply_move, captures_for_move, create_initial_board, find_legal_moves, row_col_to_index
from maiming.domain.othello.types import SIDE_BLACK, SIDE_WHITE


class OthelloRulesTests(unittest.TestCase):
    def test_initial_legal_moves_for_black_match_standard_opening(self) -> None:
        legal = set(find_legal_moves(create_initial_board(), SIDE_BLACK))
        expected = {
            row_col_to_index(2, 3),
            row_col_to_index(3, 2),
            row_col_to_index(4, 5),
            row_col_to_index(5, 4),
        }
        self.assertEqual(expected, legal)

    def test_apply_move_flips_standard_opening_disc(self) -> None:
        board = create_initial_board()
        move_index = row_col_to_index(2, 3)
        next_board, flipped = apply_move(board, side=SIDE_BLACK, index=move_index)
        self.assertEqual({row_col_to_index(3, 3)}, set(flipped))
        self.assertEqual(SIDE_BLACK, next_board[move_index])
        self.assertEqual(SIDE_BLACK, next_board[row_col_to_index(3, 3)])

    def test_captures_for_move_supports_multi_direction_flip(self) -> None:
        board = [0] * 64
        center = row_col_to_index(3, 3)

        for row, col in ((3, 0), (3, 6), (0, 3), (6, 3), (0, 0), (6, 6), (0, 6), (6, 0)):
            board[row_col_to_index(row, col)] = SIDE_BLACK

        for row, col in (
            (3, 1),
            (3, 2),
            (3, 4),
            (3, 5),
            (1, 3),
            (2, 3),
            (4, 3),
            (5, 3),
            (1, 1),
            (2, 2),
            (4, 4),
            (5, 5),
            (1, 5),
            (2, 4),
            (4, 2),
            (5, 1),
        ):
            board[row_col_to_index(row, col)] = SIDE_WHITE

        flipped = set(captures_for_move(tuple(board), side=SIDE_BLACK, index=center))
        self.assertEqual(16, len(flipped))
        self.assertIn(row_col_to_index(1, 1), flipped)
        self.assertIn(row_col_to_index(5, 5), flipped)
        self.assertIn(row_col_to_index(3, 5), flipped)


if __name__ == "__main__":
    unittest.main()
