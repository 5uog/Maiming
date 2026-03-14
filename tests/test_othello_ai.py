# FILE: tests/test_othello_ai.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.domain.othello.ai import choose_ai_move
from maiming.domain.othello.rules import create_initial_board, find_legal_moves
from maiming.domain.othello.types import OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_STRONG, OTHELLO_DIFFICULTY_WEAK, SIDE_BLACK


class OthelloAiTests(unittest.TestCase):
    def test_each_difficulty_returns_a_legal_move(self) -> None:
        board = create_initial_board()
        legal = set(find_legal_moves(board, SIDE_BLACK))

        for difficulty in (OTHELLO_DIFFICULTY_WEAK, OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_STRONG):
            move_index = choose_ai_move(board, SIDE_BLACK, difficulty, random_seed=7)
            self.assertIn(move_index, legal)

    def test_returns_none_when_no_legal_move_exists(self) -> None:
        board = tuple([SIDE_BLACK] * 64)
        self.assertIsNone(choose_ai_move(board, SIDE_BLACK, OTHELLO_DIFFICULTY_MEDIUM))


if __name__ == "__main__":
    unittest.main()
