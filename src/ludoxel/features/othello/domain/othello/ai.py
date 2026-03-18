# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/features/othello/domain/othello/ai.py
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from .rules import BOARD_SIZE, apply_move, counts_for_board, find_legal_moves, other_side
from .types import OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_WEAK, SIDE_BLACK, SIDE_WHITE, coerce_board, normalize_difficulty, normalize_side

_POSITION_WEIGHTS: tuple[int, ...] = (120, -20, 20, 5, 5, 20, -20, 120, -20, -40, -5, -5, -5, -5, -40, -20, 20, -5, 15, 3, 3, 15, -5, 20, 5, -5, 3, 3, 3, 3, -5, 5, 5, -5, 3, 3, 3, 3, -5, 5, 20, -5, 15, 3, 3, 15, -5, 20, -20, -40, -5, -5, -5, -5, -40, -20, 120, -20, 20, 5, 5, 20, -20, 120)


@dataclass(frozen=True)
class _SearchResult:
    score: float
    move_index: int | None


def _frontier_count(board: tuple[int, ...], side: int) -> int:
    target = normalize_side(side)
    count = 0
    for index, value in enumerate(board):
        if value != target:
            continue
        row = index // BOARD_SIZE
        col = index % BOARD_SIZE
        frontier = False
        for d_row in (-1, 0, 1):
            for d_col in (-1, 0, 1):
                if d_row == 0 and d_col == 0:
                    continue
                next_row = row + d_row
                next_col = col + d_col
                if 0 <= next_row < BOARD_SIZE and 0 <= next_col < BOARD_SIZE:
                    if board[next_row * BOARD_SIZE + next_col] == 0:
                        frontier = True
                        break
            if frontier:
                break
        if frontier:
            count += 1
    return int(count)


def _evaluate(board: tuple[int, ...], side: int) -> float:
    my_side = normalize_side(side)
    enemy = other_side(my_side)
    if my_side not in (SIDE_BLACK, SIDE_WHITE) or enemy not in (SIDE_BLACK, SIDE_WHITE):
        return 0.0

    my_count, enemy_count = 0, 0
    positional = 0
    for index, value in enumerate(board):
        if value == my_side:
            positional += _POSITION_WEIGHTS[index]
            my_count += 1
        elif value == enemy:
            positional -= _POSITION_WEIGHTS[index]
            enemy_count += 1

    my_moves = len(find_legal_moves(board, my_side))
    enemy_moves = len(find_legal_moves(board, enemy))
    mobility = 0.0
    if my_moves + enemy_moves > 0:
        mobility = 100.0 * float(my_moves - enemy_moves) / float(my_moves + enemy_moves)

    corners = (0, BOARD_SIZE - 1, BOARD_SIZE * (BOARD_SIZE - 1), BOARD_SIZE * BOARD_SIZE - 1)
    my_corners = 0
    enemy_corners = 0
    for corner in corners:
        if board[corner] == my_side:
            my_corners += 1
        elif board[corner] == enemy:
            enemy_corners += 1

    corner_score = 25.0 * float(my_corners - enemy_corners)
    disc_diff = 0.0
    if my_count + enemy_count > 0:
        disc_diff = 20.0 * float(my_count - enemy_count) / float(my_count + enemy_count)

    frontier_penalty = -5.0 * float(_frontier_count(board, my_side) - _frontier_count(board, enemy))
    return float(positional) + float(mobility) + float(corner_score) + float(disc_diff) + float(frontier_penalty)


def _terminal_score(board: tuple[int, ...], side: int) -> float:
    black, white = counts_for_board(board)
    my_side = normalize_side(side)
    my_count = black if my_side == SIDE_BLACK else white
    enemy_count = white if my_side == SIDE_BLACK else black
    if my_count > enemy_count:
        return 100000.0 + float(my_count - enemy_count)
    if enemy_count > my_count:
        return -100000.0 - float(enemy_count - my_count)
    return 0.0


def _alpha_beta(board: tuple[int, ...], side_to_move: int, root_side: int, depth: int, alpha: float, beta: float, deadline_s: float | None, pass_count: int) -> float:
    if deadline_s is not None and time.perf_counter() >= float(deadline_s):
        raise TimeoutError

    my_moves = find_legal_moves(board, side_to_move)
    enemy_side = other_side(side_to_move)
    enemy_moves = find_legal_moves(board, enemy_side)

    if depth <= 0:
        return _evaluate(board, root_side)

    if not my_moves and not enemy_moves:
        return _terminal_score(board, root_side)

    if not my_moves:
        if pass_count >= 1:
            return _terminal_score(board, root_side)
        return _alpha_beta(board, enemy_side, root_side, depth - 1, alpha, beta, deadline_s, pass_count + 1)

    maximizing = side_to_move == root_side
    best = -math.inf if maximizing else math.inf

    ordered_moves = sorted(my_moves, key=lambda index: _POSITION_WEIGHTS[int(index)], reverse=bool(maximizing))

    for move_index in ordered_moves:
        if deadline_s is not None and time.perf_counter() >= float(deadline_s):
            raise TimeoutError
        next_board, _flips = apply_move(board, side=side_to_move, index=int(move_index))
        child = _alpha_beta(next_board, enemy_side, root_side, depth - 1, alpha, beta, deadline_s, 0)
        if maximizing:
            best = max(best, child)
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        else:
            best = min(best, child)
            beta = min(beta, best)
            if beta <= alpha:
                break
    return float(best)


def _best_move(board: tuple[int, ...], side: int, *, depth: int, deadline_s: float | None, rng: random.Random | None = None) -> _SearchResult:
    moves = find_legal_moves(board, side)
    if not moves:
        return _SearchResult(score=0.0, move_index=None)

    best_score = -math.inf
    best_moves: list[int] = []
    enemy = other_side(side)

    ordered_moves = sorted(moves, key=lambda index: _POSITION_WEIGHTS[int(index)], reverse=True)

    for move_index in ordered_moves:
        if deadline_s is not None and time.perf_counter() >= float(deadline_s):
            raise TimeoutError
        next_board, _flips = apply_move(board, side=side, index=int(move_index))
        score = _alpha_beta(next_board, enemy, side, depth - 1, -math.inf, math.inf, deadline_s, 0)
        if score > best_score + 1e-9:
            best_score = float(score)
            best_moves = [int(move_index)]
        elif abs(float(score) - float(best_score)) <= 1e-9:
            best_moves.append(int(move_index))

    if not best_moves:
        return _SearchResult(score=0.0, move_index=None)

    chooser = rng if rng is not None else random.Random(0)
    return _SearchResult(score=float(best_score), move_index=int(chooser.choice(best_moves)))


def choose_ai_move(board: tuple[int, ...] | list[int], side: int, difficulty: str, *, random_seed: int = 0, strong_time_budget_s: float = 1.5) -> int | None:
    materialized = coerce_board(board)
    ai_side = normalize_side(side)
    if ai_side not in (SIDE_BLACK, SIDE_WHITE):
        return None

    legal_moves = find_legal_moves(materialized, ai_side)
    if not legal_moves:
        return None

    mode = normalize_difficulty(difficulty)
    rng = random.Random(int(random_seed))

    if mode == OTHELLO_DIFFICULTY_WEAK:
        return _best_move(materialized, ai_side, depth=1, deadline_s=None, rng=rng).move_index

    if mode == OTHELLO_DIFFICULTY_MEDIUM:
        return _best_move(materialized, ai_side, depth=3, deadline_s=None).move_index

    deadline = time.perf_counter() + max(0.1, float(strong_time_budget_s))
    best_result = _SearchResult(score=-math.inf, move_index=int(legal_moves[0]))
    for depth in range(1, 6):
        try:
            result = _best_move(materialized, ai_side, depth=depth, deadline_s=deadline)
        except TimeoutError:
            break
        if result.move_index is not None:
            best_result = result
        if time.perf_counter() >= deadline:
            break
    return best_result.move_index
