# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

import math
import random
import time

from .evaluation_profile import POSITION_WEIGHTS, evaluation_weights
from .insane_engine import InsaneSearchCache, analyze_insane_position, opening_book_moves
from ..game.rules import BOARD_SIZE, apply_move, counts_for_board, find_legal_moves, other_side
from ..game.types import DEFAULT_OTHELLO_SACRIFICE_LEVEL, OTHELLO_DIFFICULTY_INSANE, OTHELLO_DIFFICULTY_INSANE_PLUS, OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_WEAK, SIDE_BLACK, SIDE_WHITE, OthelloAnalysis, OthelloDepthSample, coerce_board, normalize_difficulty, normalize_sacrifice_level, normalize_side

_POSITION_WEIGHTS: tuple[int, ...] = POSITION_WEIGHTS


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


def _evaluate(board: tuple[int, ...], side: int, *, sacrifice_level: int=DEFAULT_OTHELLO_SACRIFICE_LEVEL) -> float:
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

    disc_weight, mobility_weight, corner_weight, frontier_weight = evaluation_weights(int(sacrifice_level))
    frontier_penalty = -5.0 * float(_frontier_count(board, my_side) - _frontier_count(board, enemy))
    return float(positional) + float(mobility) * float(mobility_weight) + float(corner_score) * float(corner_weight) + float(disc_diff) * float(disc_weight) + float(frontier_penalty) * float(frontier_weight)


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


def _alpha_beta(board: tuple[int, ...], side_to_move: int, root_side: int, depth: int, alpha: float, beta: float, deadline_s: float | None, pass_count: int, *, sacrifice_level: int) -> float:
    if deadline_s is not None and time.perf_counter() >= float(deadline_s):
        raise TimeoutError

    my_moves = find_legal_moves(board, side_to_move)
    enemy_side = other_side(side_to_move)
    enemy_moves = find_legal_moves(board, enemy_side)

    if depth <= 0:
        return _evaluate(board, root_side, sacrifice_level=int(sacrifice_level))

    if not my_moves and not enemy_moves:
        return _terminal_score(board, root_side)

    if not my_moves:
        if pass_count >= 1:
            return _terminal_score(board, root_side)
        return _alpha_beta(board, enemy_side, root_side, depth - 1, alpha, beta, deadline_s, pass_count + 1, sacrifice_level=int(sacrifice_level))

    maximizing = side_to_move == root_side
    best = -math.inf if maximizing else math.inf

    ordered_moves = sorted(my_moves, key=lambda index: _POSITION_WEIGHTS[int(index)], reverse=bool(maximizing))

    for move_index in ordered_moves:
        if deadline_s is not None and time.perf_counter() >= float(deadline_s):
            raise TimeoutError
        next_board, _flips = apply_move(board, side=side_to_move, index=int(move_index))
        child = _alpha_beta(next_board, enemy_side, root_side, depth - 1, alpha, beta, deadline_s, 0, sacrifice_level=int(sacrifice_level))
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


def _best_move(board: tuple[int, ...], side: int, *, depth: int, deadline_s: float | None, rng: random.Random | None=None, sacrifice_level: int=DEFAULT_OTHELLO_SACRIFICE_LEVEL) -> _SearchResult:
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
        score = _alpha_beta(next_board, enemy, side, depth - 1, -math.inf, math.inf, deadline_s, 0, sacrifice_level=int(sacrifice_level))
        if score > best_score + 1e-9:
            best_score = float(score)
            best_moves = [int(move_index)]
        elif abs(float(score) - float(best_score)) <= 1e-9:
            best_moves.append(int(move_index))

    if not best_moves:
        return _SearchResult(score=0.0, move_index=None)

    chooser = rng if rng is not None else random.Random(0)
    return _SearchResult(score=float(best_score), move_index=int(chooser.choice(best_moves)))


def _select_opening_book_move(board: tuple[int, ...], side: int, legal_moves: tuple[int, ...], *, random_seed: int, cache: InsaneSearchCache | None) -> int | None:
    if not legal_moves:
        return None
    legal_moves_set = set(int(move) for move in legal_moves)
    candidate_moves = tuple(int(move) for move in opening_book_moves(cache, board, side) if int(move) in legal_moves_set)
    if not candidate_moves:
        return None
    chooser = random.Random(int(random_seed))
    return int(chooser.choice(tuple(sorted(candidate_moves))))


def _forecast_line(board: tuple[int, ...], side: int, difficulty: str, *, random_seed: int, project_root=None, sacrifice_level: int, hash_level: int, match_generation: int, insane_cache: InsaneSearchCache | None, strong_time_budget_s: float, insane_time_budget_s: float, max_plies: int=6) -> tuple[int, ...]:
    materialized = coerce_board(board)
    current_side = normalize_side(side)
    line: list[int] = []

    for ply_index in range(max(0, int(max_plies))):
        if current_side not in (SIDE_BLACK, SIDE_WHITE):
            break
        move_index = choose_ai_move(materialized, current_side, difficulty, random_seed=int(random_seed + ply_index * 17), project_root=project_root, strong_time_budget_s=float(strong_time_budget_s), insane_time_budget_s=float(insane_time_budget_s), match_generation=int(match_generation), insane_cache=insane_cache, sacrifice_level=int(sacrifice_level), hash_level=int(hash_level))
        if move_index is None:
            break
        line.append(int(move_index))
        materialized, _flipped = apply_move(materialized, side=current_side, index=int(move_index))
        next_side = other_side(current_side)
        if not find_legal_moves(materialized, next_side):
            fallback_side = other_side(next_side)
            if not find_legal_moves(materialized, fallback_side):
                break
            next_side = fallback_side
        current_side = int(next_side)

    return tuple(line)


def analyze_position(board: tuple[int, ...] | list[int], side: int, difficulty: str, *, random_seed: int=0, project_root=None, strong_time_budget_s: float=1.5, insane_time_budget_s: float=4.0, match_generation: int=0, insane_cache: InsaneSearchCache | None=None, sacrifice_level: int=DEFAULT_OTHELLO_SACRIFICE_LEVEL, hash_level: int=2, include_forecast_line: bool=True) -> OthelloAnalysis:
    materialized = coerce_board(board)
    ai_side = normalize_side(side)
    if ai_side not in (SIDE_BLACK, SIDE_WHITE):
        return OthelloAnalysis().normalized()

    legal_moves = find_legal_moves(materialized, ai_side)
    if not legal_moves:
        return OthelloAnalysis(side_to_move=int(ai_side), best_move_index=None, best_line=(), score=0.0, solved=False, depth_reached=0, depth_samples=()).normalized()

    mode = normalize_difficulty(difficulty)
    rng = random.Random(int(random_seed))
    normalized_sacrifice_level = normalize_sacrifice_level(sacrifice_level, default=DEFAULT_OTHELLO_SACRIFICE_LEVEL)
    forecast_strong_budget_s = float(min(0.12, max(0.03, float(strong_time_budget_s) * 0.15)))
    forecast_insane_budget_s = float(min(0.18, max(0.04, float(insane_time_budget_s) * 0.10)))

    def build_forecast(max_plies: int) -> tuple[int, ...]:
        if not bool(include_forecast_line):
            return ()
        return _forecast_line(materialized, ai_side, mode, random_seed=int(random_seed), project_root=project_root, sacrifice_level=int(normalized_sacrifice_level), hash_level=int(hash_level), match_generation=int(match_generation), insane_cache=insane_cache, strong_time_budget_s=float(forecast_strong_budget_s), insane_time_budget_s=float(forecast_insane_budget_s), max_plies=int(max_plies))

    if mode == OTHELLO_DIFFICULTY_WEAK:
        result = _best_move(materialized, ai_side, depth=1, deadline_s=None, rng=rng, sacrifice_level=int(normalized_sacrifice_level))
        return OthelloAnalysis(side_to_move=int(ai_side), best_move_index=result.move_index, best_line=build_forecast(4), score=float(result.score), solved=False, depth_reached=1, depth_samples=(OthelloDepthSample(depth=1, score=float(result.score)),)).normalized()

    if mode == OTHELLO_DIFFICULTY_MEDIUM:
        result = _best_move(materialized, ai_side, depth=3, deadline_s=None, sacrifice_level=int(normalized_sacrifice_level))
        return OthelloAnalysis(side_to_move=int(ai_side), best_move_index=result.move_index, best_line=build_forecast(6), score=float(result.score), solved=False, depth_reached=3, depth_samples=(OthelloDepthSample(depth=3, score=float(result.score)),)).normalized()

    if mode == OTHELLO_DIFFICULTY_INSANE:
        active_cache = insane_cache or InsaneSearchCache()
        active_cache.prepare(int(match_generation), project_root=project_root, hash_level=int(hash_level), sacrifice_level=int(normalized_sacrifice_level))
        analysis = analyze_insane_position(materialized, ai_side, random_seed=int(random_seed), time_budget_s=float(insane_time_budget_s), cache=active_cache)
        return OthelloAnalysis(side_to_move=int(ai_side), best_move_index=analysis.best_move_index, best_line=build_forecast(8), score=float(analysis.score), solved=bool(analysis.solved), depth_reached=int(analysis.depth_reached), depth_samples=tuple(OthelloDepthSample(depth=int(sample.depth), score=float(sample.score), solved=bool(sample.solved)) for sample in tuple(analysis.depth_samples))).normalized()

    if mode == OTHELLO_DIFFICULTY_INSANE_PLUS:
        active_cache = insane_cache or InsaneSearchCache()
        active_cache.prepare(int(match_generation), project_root=project_root, hash_level=int(hash_level), sacrifice_level=int(normalized_sacrifice_level))
        analysis = analyze_insane_position(materialized, ai_side, random_seed=int(random_seed), time_budget_s=float(insane_time_budget_s), cache=active_cache)
        book_move_index = _select_opening_book_move(materialized, ai_side, legal_moves, random_seed=int(random_seed), cache=active_cache)
        best_move_index = analysis.best_move_index if book_move_index is None else int(book_move_index)
        return OthelloAnalysis(side_to_move=int(ai_side), best_move_index=best_move_index, best_line=build_forecast(8), score=float(analysis.score), solved=bool(analysis.solved), depth_reached=int(analysis.depth_reached), depth_samples=tuple(OthelloDepthSample(depth=int(sample.depth), score=float(sample.score), solved=bool(sample.solved)) for sample in tuple(analysis.depth_samples))).normalized()

    deadline = time.perf_counter() + max(0.1, float(strong_time_budget_s))
    best_result = _SearchResult(score=-math.inf, move_index=int(legal_moves[0]))
    depth_samples: list[OthelloDepthSample] = []
    best_depth = 0
    for depth in range(1, 6):
        try:
            result = _best_move(materialized, ai_side, depth=depth, deadline_s=deadline, sacrifice_level=int(normalized_sacrifice_level))
        except TimeoutError:
            break
        if result.move_index is not None:
            best_result = result
            best_depth = int(depth)
            depth_samples.append(OthelloDepthSample(depth=int(depth), score=float(result.score)))
        if time.perf_counter() >= deadline:
            break
    return OthelloAnalysis(side_to_move=int(ai_side), best_move_index=best_result.move_index, best_line=build_forecast(6), score=float(best_result.score if math.isfinite(best_result.score) else 0.0), solved=False, depth_reached=int(best_depth), depth_samples=tuple(depth_samples)).normalized()


def choose_ai_move(board: tuple[int, ...] | list[int], side: int, difficulty: str, *, random_seed: int=0, project_root=None, strong_time_budget_s: float=1.5, insane_time_budget_s: float=4.0, match_generation: int=0, insane_cache: InsaneSearchCache | None=None, sacrifice_level: int=DEFAULT_OTHELLO_SACRIFICE_LEVEL, hash_level: int=2) -> int | None:
    materialized = coerce_board(board)
    ai_side = normalize_side(side)
    mode = normalize_difficulty(difficulty)
    normalized_sacrifice_level = normalize_sacrifice_level(sacrifice_level, default=DEFAULT_OTHELLO_SACRIFICE_LEVEL)
    if mode == OTHELLO_DIFFICULTY_INSANE_PLUS and ai_side in (SIDE_BLACK, SIDE_WHITE):
        legal_moves = find_legal_moves(materialized, ai_side)
        if legal_moves:
            active_cache = insane_cache or InsaneSearchCache()
            active_cache.prepare(int(match_generation), project_root=project_root, hash_level=int(hash_level), sacrifice_level=int(normalized_sacrifice_level))
            book_move_index = _select_opening_book_move(materialized, ai_side, legal_moves, random_seed=int(random_seed), cache=active_cache)
            if book_move_index is not None:
                return int(book_move_index)
    analysis = analyze_position(board, side, difficulty, random_seed=int(random_seed), project_root=project_root, strong_time_budget_s=float(strong_time_budget_s), insane_time_budget_s=float(insane_time_budget_s), match_generation=int(match_generation), insane_cache=insane_cache, sacrifice_level=int(sacrifice_level), hash_level=int(hash_level), include_forecast_line=False)
    return analysis.best_move_index
