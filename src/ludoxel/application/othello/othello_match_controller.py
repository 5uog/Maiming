# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/othello/othello_match_controller.py
from __future__ import annotations

from dataclasses import replace

from ...domain.othello.rules import apply_move, counts_for_board, create_initial_board, find_legal_moves, winner_for_board
from ...domain.othello.types import OTHELLO_GAME_STATE_AI_TURN, OTHELLO_GAME_STATE_ANIMATING, OTHELLO_GAME_STATE_FINISHED, OTHELLO_GAME_STATE_IDLE, OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_TIME_CONTROL_NONE, SIDE_BLACK, SIDE_WHITE, OthelloAnimationState, OthelloGameState, OthelloSettings, other_side, side_name


def _turn_status_for_player_side(player_side: int, current_turn: int) -> str:
    if int(current_turn) == int(player_side):
        return OTHELLO_GAME_STATE_PLAYER_TURN
    return OTHELLO_GAME_STATE_AI_TURN


class OthelloMatchController:

    def __init__(self, *, default_settings: OthelloSettings | None=None, game_state: OthelloGameState | None=None) -> None:
        self._default_settings = (default_settings or OthelloSettings()).normalized()
        self._state = (game_state or OthelloGameState()).normalized()
        self._state = self._coerce_loaded_state(self._state)

    def default_settings(self) -> OthelloSettings:
        return self._default_settings.normalized()

    def set_default_settings(self, settings: OthelloSettings) -> None:
        self._default_settings = settings.normalized()

    def game_state(self) -> OthelloGameState:
        return self._state.normalized()

    def set_game_state(self, game_state: OthelloGameState) -> None:
        self._state = self._coerce_loaded_state(game_state.normalized())

    def reset_to_idle(self) -> None:
        self._state = OthelloGameState(message="Right-click Start to begin a match. Use left click to place a disc.").normalized()

    def start_new_match(self) -> OthelloGameState:
        settings = self._default_settings.normalized()
        player_side = int(settings.player_side)
        ai_side = int(other_side(player_side))
        current_turn = int(SIDE_BLACK)
        time_limit_s = settings.default_time_limit_s()

        self._state = OthelloGameState(status=OTHELLO_GAME_STATE_IDLE, board=create_initial_board(), settings=settings, player_side=player_side, ai_side=ai_side, current_turn=current_turn, black_time_remaining_s=time_limit_s, white_time_remaining_s=time_limit_s, move_count=0, consecutive_passes=0, winner=None, message="Match initialized.", last_move_index=None, animations=(), match_generation=int(self._state.match_generation) + 1, legal_moves=(), thinking=False).normalized()
        self._state = self._resolve_turn_transition(message_prefix="Match started.")
        return self.game_state()

    def restart_match(self) -> OthelloGameState:
        return self.start_new_match()

    def can_player_move(self, square_index: int) -> bool:
        state = self._state.normalized()
        return bool(state.status == OTHELLO_GAME_STATE_PLAYER_TURN and int(square_index) in set(state.legal_moves))

    def set_ai_thinking(self, thinking: bool) -> None:
        self._state = replace(self._state, thinking=bool(thinking)).normalized()

    def settle_animations(self) -> OthelloGameState:
        state = self._state.normalized()
        if state.status != OTHELLO_GAME_STATE_ANIMATING or not state.animations:
            self._state = replace(state, animations=(), thinking=False).normalized()
            return self.game_state()
        self._state = replace(state, animations=(), thinking=False).normalized()
        self._state = self._resolve_turn_transition(message_prefix="Animation settled.")
        return self.game_state()

    def tick(self, dt: float, *, paused: bool) -> OthelloGameState:
        step = max(0.0, float(dt))
        state = self._state.normalized()

        if state.status == OTHELLO_GAME_STATE_ANIMATING and state.animations:
            next_animations: list[OthelloAnimationState] = []
            for animation in state.animations:
                advanced = animation.normalized()
                elapsed = min(float(advanced.duration_s), float(advanced.elapsed_s) + step)
                if elapsed + 1e-9 < float(advanced.duration_s):
                    next_animations.append(replace(advanced, elapsed_s=float(elapsed)).normalized())
            if next_animations:
                self._state = replace(state, animations=tuple(next_animations)).normalized()
                return self.game_state()
            self._state = replace(state, animations=()).normalized()
            self._state = self._resolve_turn_transition(message_prefix="Move resolved.")
            return self.game_state()

        if paused or step <= 1e-9:
            self._state = state
            return self.game_state()

        if state.status not in (OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_GAME_STATE_AI_TURN):
            self._state = state
            return self.game_state()

        if state.settings.time_control == OTHELLO_TIME_CONTROL_NONE:
            self._state = state
            return self.game_state()

        black_time = state.black_time_remaining_s
        white_time = state.white_time_remaining_s

        if state.current_turn == SIDE_BLACK and black_time is not None:
            black_time = max(0.0, float(black_time) - step)
        elif state.current_turn == SIDE_WHITE and white_time is not None:
            white_time = max(0.0, float(white_time) - step)

        timed_state = replace(state, black_time_remaining_s=black_time, white_time_remaining_s=white_time).normalized()

        if (timed_state.current_turn == SIDE_BLACK and black_time is not None and black_time <= 1e-9) or (timed_state.current_turn == SIDE_WHITE and white_time is not None and white_time <= 1e-9):
            winner = side_name(other_side(timed_state.current_turn))
            self._state = replace(timed_state, status=OTHELLO_GAME_STATE_FINISHED, legal_moves=(), winner=winner, thinking=False, message=f"{side_name(timed_state.current_turn).title()} ran out of time.").normalized()
            return self.game_state()

        self._state = timed_state
        return self.game_state()

    def submit_player_move(self, square_index: int) -> bool:
        state = self._state.normalized()
        if state.status != OTHELLO_GAME_STATE_PLAYER_TURN:
            return False
        if int(square_index) not in set(state.legal_moves):
            return False
        self._apply_turn_move(side=state.player_side, square_index=int(square_index))
        return True

    def submit_ai_move(self, square_index: int | None) -> bool:
        state = self._state.normalized()
        if state.status != OTHELLO_GAME_STATE_AI_TURN:
            return False

        legal = tuple(state.legal_moves)
        if not legal:
            self._state = replace(state, thinking=False).normalized()
            self._state = self._resolve_turn_transition(message_prefix="AI had no legal move.")
            return False

        move_index = legal[0] if square_index is None else int(square_index)
        if move_index not in set(legal):
            move_index = int(legal[0])

        self._apply_turn_move(side=state.ai_side, square_index=int(move_index))
        return True

    def _apply_turn_move(self, *, side: int, square_index: int) -> None:
        state = self._state.normalized()
        next_board, flipped = apply_move(state.board, side=side, index=int(square_index))
        animations = tuple(OthelloAnimationState(square_index=int(index), from_side=other_side(side), to_side=side).normalized() for index in flipped)

        updated = replace(state, board=next_board, current_turn=other_side(side), move_count=int(state.move_count) + 1, consecutive_passes=0, last_move_index=int(square_index), animations=animations, status=OTHELLO_GAME_STATE_ANIMATING if animations else OTHELLO_GAME_STATE_IDLE, thinking=False, legal_moves=(), message=f"{side_name(side).title()} moved to {int(square_index)}.").normalized()
        self._state = updated
        if not animations:
            self._state = self._resolve_turn_transition(message_prefix="Move applied.")

    def _coerce_loaded_state(self, state: OthelloGameState) -> OthelloGameState:
        normalized = state.normalized()
        if normalized.status == OTHELLO_GAME_STATE_IDLE:
            return replace(normalized, legal_moves=(), thinking=False).normalized()
        if normalized.status == OTHELLO_GAME_STATE_FINISHED:
            return replace(normalized, legal_moves=(), thinking=False, animations=()).normalized()
        if normalized.status == OTHELLO_GAME_STATE_ANIMATING:
            normalized = replace(normalized, animations=(), thinking=False).normalized()
        self._state = normalized
        return self._resolve_turn_transition(message_prefix="Match restored.")

    def _resolve_turn_transition(self, *, message_prefix: str) -> OthelloGameState:
        state = self._state.normalized()
        if state.status == OTHELLO_GAME_STATE_FINISHED:
            self._state = replace(state, legal_moves=(), thinking=False, animations=()).normalized()
            return self.game_state()

        current_side = int(state.current_turn)
        legal_moves = find_legal_moves(state.board, current_side)
        if legal_moves:
            next_status = _turn_status_for_player_side(state.player_side, current_side)
            message = f"{message_prefix} {side_name(current_side).title()} to move."
            self._state = replace(state, status=next_status, legal_moves=tuple(legal_moves), thinking=False, message=message).normalized()
            return self.game_state()

        other = int(other_side(current_side))
        other_legal_moves = find_legal_moves(state.board, other)
        if other_legal_moves:
            message = f"{message_prefix} {side_name(current_side).title()} must pass."
            next_status = _turn_status_for_player_side(state.player_side, other)
            self._state = replace(state, current_turn=other, legal_moves=tuple(other_legal_moves), consecutive_passes=min(2, int(state.consecutive_passes) + 1), status=next_status, thinking=False, message=message).normalized()
            return self.game_state()

        winner = winner_for_board(state.board)
        black, white = counts_for_board(state.board)
        message = f"{message_prefix} Match finished. Black {int(black)} - White {int(white)}."
        self._state = replace(state, status=OTHELLO_GAME_STATE_FINISHED, legal_moves=(), winner=winner, thinking=False, animations=(), message=message).normalized()
        return self.game_state()
