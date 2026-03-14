# FILE: tests/test_othello_match_controller.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.application.othello.othello_match_controller import OthelloMatchController
from maiming.domain.othello.rules import row_col_to_index
from maiming.domain.othello.types import OTHELLO_GAME_STATE_FINISHED, OTHELLO_GAME_STATE_PLAYER_TURN, SIDE_BLACK, SIDE_WHITE, OthelloGameState, OthelloSettings


class OthelloMatchControllerTests(unittest.TestCase):
    def test_player_second_starts_on_ai_turn(self) -> None:
        controller = OthelloMatchController(default_settings=OthelloSettings(player_side=SIDE_WHITE))
        state = controller.start_new_match()
        self.assertEqual(SIDE_BLACK, state.current_turn)
        self.assertEqual(SIDE_WHITE, state.player_side)
        self.assertNotEqual(OTHELLO_GAME_STATE_PLAYER_TURN, state.status)

    def test_forced_pass_transfers_turn(self) -> None:
        board = [SIDE_BLACK] * 64
        board[row_col_to_index(0, 0)] = 0
        board[row_col_to_index(0, 1)] = SIDE_WHITE
        board[row_col_to_index(0, 2)] = SIDE_BLACK

        controller = OthelloMatchController(
            game_state=OthelloGameState(
                status=OTHELLO_GAME_STATE_PLAYER_TURN,
                board=tuple(board),
                player_side=SIDE_BLACK,
                ai_side=SIDE_WHITE,
                current_turn=SIDE_WHITE,
            )
        )
        state = controller.game_state()
        self.assertEqual(SIDE_BLACK, state.current_turn)
        self.assertEqual(OTHELLO_GAME_STATE_PLAYER_TURN, state.status)
        self.assertIn(row_col_to_index(0, 0), set(state.legal_moves))

    def test_time_expiry_finishes_match(self) -> None:
        controller = OthelloMatchController()
        controller.start_new_match()
        controller.set_game_state(
            OthelloGameState(
                status=OTHELLO_GAME_STATE_PLAYER_TURN,
                board=controller.game_state().board,
                settings=OthelloSettings(),
                player_side=SIDE_BLACK,
                ai_side=SIDE_WHITE,
                current_turn=SIDE_BLACK,
                black_time_remaining_s=0.05,
                white_time_remaining_s=1200.0,
            )
        )
        state = controller.tick(0.10, paused=False)
        self.assertEqual(OTHELLO_GAME_STATE_FINISHED, state.status)
        self.assertEqual("white", state.winner)


if __name__ == "__main__":
    unittest.main()
