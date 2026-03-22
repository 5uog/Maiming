# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field

import random
import time

from .opening_book import OpeningBook, load_opening_book
from .types import BOARD_CELL_COUNT, SIDE_BLACK, SIDE_WHITE, coerce_board, normalize_side

_FULL_MASK = (1 << BOARD_CELL_COUNT) - 1
_FILE_A = 0x0101010101010101
_FILE_H = 0x8080808080808080
_NOT_FILE_A = _FULL_MASK ^ _FILE_A
_NOT_FILE_H = _FULL_MASK ^ _FILE_H
_CORNERS = (0, 7, 56, 63)
_X_SQUARES = (9, 14, 49, 54)
_C_SQUARES = (1, 6, 8, 15, 48, 55, 57, 62)
_WIN_SCORE = 1_000_000
_LOSS_SCORE = -_WIN_SCORE
_BOUND_EXACT = 0
_BOUND_LOWER = 1
_BOUND_UPPER = -1

_POSITION_WEIGHTS: tuple[int, ...] = (120, -20, 20, 5, 5, 20, -20, 120, -20, -40, -5, -5, -5, -5, -40, -20, 20, -5, 15, 3, 3, 15, -5, 20, 5, -5, 3, 3, 3, 3, -5, 5, 5, -5, 3, 3, 3, 3, -5, 5, 20, -5, 15, 3, 3, 15, -5, 20, -20, -40, -5, -5, -5, -5, -40, -20, 120, -20, 20, 5, 5, 20, -20, 120)
_POSITION_SQUARE_MASKS: tuple[int, ...] = tuple(1 << index for index in range(BOARD_CELL_COUNT))


def _shift_east(bits: int) -> int:
    return ((int(bits) & _NOT_FILE_H) << 1) & _FULL_MASK


def _shift_west(bits: int) -> int:
    return ((int(bits) & _NOT_FILE_A) >> 1) & _FULL_MASK


def _shift_south(bits: int) -> int:
    return (int(bits) << 8) & _FULL_MASK


def _shift_north(bits: int) -> int:
    return (int(bits) >> 8) & _FULL_MASK


def _shift_south_east(bits: int) -> int:
    return ((int(bits) & _NOT_FILE_H) << 9) & _FULL_MASK


def _shift_south_west(bits: int) -> int:
    return ((int(bits) & _NOT_FILE_A) << 7) & _FULL_MASK


def _shift_north_east(bits: int) -> int:
    return ((int(bits) & _NOT_FILE_H) >> 7) & _FULL_MASK


def _shift_north_west(bits: int) -> int:
    return ((int(bits) & _NOT_FILE_A) >> 9) & _FULL_MASK


_SHIFT_FUNCS = (_shift_east, _shift_west, _shift_south, _shift_north, _shift_south_east, _shift_south_west, _shift_north_east, _shift_north_west)


def _bitboards_from_board(board: tuple[int, ...] | list[int]) -> tuple[int, int]:
    black = 0
    white = 0
    for index, value in enumerate(coerce_board(board)):
        mask = 1 << int(index)
        if int(value) == SIDE_BLACK:
            black |= mask
        elif int(value) == SIDE_WHITE:
            white |= mask
    return (int(black), int(white))


def _legal_moves_bitboard(player_bits: int, opponent_bits: int) -> int:
    player = int(player_bits)
    opponent = int(opponent_bits)
    empty = (~(player | opponent)) & _FULL_MASK
    moves = 0
    for shift in _SHIFT_FUNCS:
        frontier = shift(player) & opponent
        captured = frontier
        for _ in range(5):
            frontier = shift(frontier) & opponent
            if frontier == 0:
                break
            captured |= frontier
        moves |= shift(captured) & empty
    return int(moves)


def _bitboard_to_moves(bits: int) -> tuple[int, ...]:
    out: list[int] = []
    remaining = int(bits)
    while remaining:
        lsb = remaining & -remaining
        out.append(int(lsb.bit_length() - 1))
        remaining ^= lsb
    return tuple(out)


def _capture_line(move_bit: int, player_bits: int, opponent_bits: int, shift) -> int:
    cursor = shift(int(move_bit))
    flips = 0
    while cursor and (cursor & int(opponent_bits)):
        flips |= cursor
        cursor = shift(cursor)
    if cursor & int(player_bits):
        return int(flips)
    return 0


def _apply_move_bits(player_bits: int, opponent_bits: int, move_index: int) -> tuple[int, int]:
    move_bit = 1 << int(move_index)
    flips = 0
    for shift in _SHIFT_FUNCS:
        flips |= _capture_line(move_bit, int(player_bits), int(opponent_bits), shift)
    next_player = int(player_bits) | int(move_bit) | int(flips)
    next_opponent = int(opponent_bits) & ~int(flips)
    return (int(next_player), int(next_opponent))


def _bit_count(bits: int) -> int:
    return int(int(bits).bit_count())


def _position_score(player_bits: int, opponent_bits: int) -> int:
    score = 0
    for index, weight in enumerate(_POSITION_WEIGHTS):
        mask = _POSITION_SQUARE_MASKS[int(index)]
        if int(player_bits) & mask:
            score += int(weight)
        elif int(opponent_bits) & mask:
            score -= int(weight)
    return int(score)


def _corner_closeness_penalty(player_bits: int, opponent_bits: int) -> int:
    score = 0
    corners = ((0,(1, 8, 9)),(7,(6, 14, 15)),(56,(48, 49, 57)),(63,(54, 55, 62)))
    for corner, adjacent in corners:
        corner_mask = 1 << int(corner)
        if ((int(player_bits) | int(opponent_bits)) & corner_mask) != 0:
            continue
        for square in adjacent:
            mask = 1 << int(square)
            if int(player_bits) & mask:
                score -= 30
            elif int(opponent_bits) & mask:
                score += 30
    return int(score)


def _adjacent_bits(bits: int) -> int:
    src = int(bits)
    return int((_shift_east(src) | _shift_west(src) | _shift_south(src) | _shift_north(src) | _shift_south_east(src) | _shift_south_west(src) | _shift_north_east(src) | _shift_north_west(src)) & _FULL_MASK)


def _frontier_score(player_bits: int, opponent_bits: int) -> int:
    empty = (~(int(player_bits) | int(opponent_bits))) & _FULL_MASK
    adjacent_to_empty = _adjacent_bits(empty)
    player_frontier = _bit_count(int(player_bits) & int(adjacent_to_empty))
    opponent_frontier = _bit_count(int(opponent_bits) & int(adjacent_to_empty))
    return int((opponent_frontier - player_frontier) * 18)


def _mobility_score(player_bits: int, opponent_bits: int) -> int:
    my_moves = _bit_count(_legal_moves_bitboard(int(player_bits), int(opponent_bits)))
    enemy_moves = _bit_count(_legal_moves_bitboard(int(opponent_bits), int(player_bits)))
    actual = 0
    if (my_moves + enemy_moves) > 0:
        actual = int(round(180.0 * float(my_moves - enemy_moves) / float(my_moves + enemy_moves)))

    potential_my = _bit_count(_adjacent_bits(int(opponent_bits)) & (~(int(player_bits) | int(opponent_bits)) & _FULL_MASK))
    potential_enemy = _bit_count(_adjacent_bits(int(player_bits)) & (~(int(player_bits) | int(opponent_bits)) & _FULL_MASK))
    potential = 0
    if (potential_my + potential_enemy) > 0:
        potential = int(round(60.0 * float(potential_my - potential_enemy) / float(potential_my + potential_enemy)))
    return int(actual + potential)


def _corner_score(player_bits: int, opponent_bits: int) -> int:
    player_corners = 0
    opponent_corners = 0
    for index in _CORNERS:
        mask = 1 << int(index)
        if int(player_bits) & mask:
            player_corners += 1
        elif int(opponent_bits) & mask:
            opponent_corners += 1
    return int((player_corners - opponent_corners) * 600)


def _parity_score(player_bits: int, opponent_bits: int) -> int:
    empties = BOARD_CELL_COUNT - _bit_count(int(player_bits) | int(opponent_bits))
    if empties <= 0:
        return 0
    return 22 if (empties & 1) == 1 else -22


def _disc_score(player_bits: int, opponent_bits: int) -> int:
    player_count = _bit_count(player_bits)
    opponent_count = _bit_count(opponent_bits)
    total = player_count + opponent_count
    if total <= 0:
        return 0
    return int(round(120.0 * float(player_count - opponent_count) / float(total)))


def _terminal_score(player_bits: int, opponent_bits: int) -> int:
    delta = _bit_count(player_bits) - _bit_count(opponent_bits)
    if delta > 0:
        return int(_WIN_SCORE + delta * 1024)
    if delta < 0:
        return int(_LOSS_SCORE + delta * 1024)
    return 0


def _evaluate(player_bits: int, opponent_bits: int) -> int:
    empties = BOARD_CELL_COUNT - _bit_count(int(player_bits) | int(opponent_bits))
    stage = 1.0 - (float(empties) / float(BOARD_CELL_COUNT))
    disc_weight = int(round(30.0 + stage * 90.0))
    score = 0
    score += _position_score(int(player_bits), int(opponent_bits))
    score += _corner_score(int(player_bits), int(opponent_bits))
    score += _corner_closeness_penalty(int(player_bits), int(opponent_bits))
    score += _mobility_score(int(player_bits), int(opponent_bits))
    score += _frontier_score(int(player_bits), int(opponent_bits))
    score += _parity_score(int(player_bits), int(opponent_bits))
    score += int(round(_disc_score(int(player_bits), int(opponent_bits)) * float(disc_weight) / 100.0))
    return int(score)


@dataclass(frozen=True)
class _TranspositionEntry:
    depth: int
    score: int
    bound: int
    best_move: int | None


@dataclass
class InsaneSearchCache:
    generation: int = -1
    transposition: dict[tuple[int, int], _TranspositionEntry] = field(default_factory=dict)
    exact_transposition: dict[tuple[int, int, int], int] = field(default_factory=dict)
    opening_book: OpeningBook = field(default_factory=load_opening_book)
    exact_threshold: int = 14

    def prepare(self, generation: int) -> None:
        normalized = int(max(0, int(generation)))
        if normalized == int(self.generation):
            return
        self.generation = int(normalized)
        self.transposition.clear()
        self.exact_transposition.clear()


def _ordering_bonus(move_index: int) -> int:
    move = int(move_index)
    if move in _CORNERS:
        return 50_000
    if move in _X_SQUARES:
        return -9_000
    if move in _C_SQUARES:
        return -4_500
    return int(_POSITION_WEIGHTS[move] * 32)


def _ordered_moves(player_bits: int, opponent_bits: int, legal_moves: tuple[int, ...], tt_move: int | None) -> tuple[int, ...]:

    def sort_key(move_index: int) -> tuple[int, int]:
        next_player, next_opponent = _apply_move_bits(int(player_bits), int(opponent_bits), int(move_index))
        reply_count = _bit_count(_legal_moves_bitboard(int(next_opponent), int(next_player)))
        score = _ordering_bonus(int(move_index)) - (reply_count * 96)
        if tt_move is not None and int(move_index) == int(tt_move):
            score += 100_000
        return (-int(score), int(move_index))

    return tuple(sorted((int(move) for move in legal_moves), key=sort_key))


def _check_deadline(deadline_s: float | None) -> None:
    if deadline_s is not None and time.perf_counter() >= float(deadline_s):
        raise TimeoutError


def _solve_exact(cache: InsaneSearchCache, player_bits: int, opponent_bits: int, alpha: int, beta: int, deadline_s: float | None, pass_count: int) -> int:
    _check_deadline(deadline_s)

    legal_bb = _legal_moves_bitboard(int(player_bits), int(opponent_bits))
    if legal_bb == 0:
        opponent_legal_bb = _legal_moves_bitboard(int(opponent_bits), int(player_bits))
        if opponent_legal_bb == 0:
            return _terminal_score(int(player_bits), int(opponent_bits))
        return -_solve_exact(cache, int(opponent_bits), int(player_bits), -int(beta), -int(alpha), deadline_s, int(pass_count) + 1)

    key = (int(player_bits), int(opponent_bits), int(pass_count))
    cached = cache.exact_transposition.get(key)
    if cached is not None:
        return int(cached)

    best = _LOSS_SCORE
    for move_index in _ordered_moves(int(player_bits), int(opponent_bits), _bitboard_to_moves(legal_bb), None):
        next_player, next_opponent = _apply_move_bits(int(player_bits), int(opponent_bits), int(move_index))
        score = -_solve_exact(cache, int(next_opponent), int(next_player), -int(beta), -int(alpha), deadline_s, 0)
        if score > int(best):
            best = int(score)
        if int(best) > int(alpha):
            alpha = int(best)
        if int(alpha) >= int(beta):
            break

    cache.exact_transposition[key] = int(best)
    return int(best)


def _negamax(cache: InsaneSearchCache, player_bits: int, opponent_bits: int, depth: int, alpha: int, beta: int, deadline_s: float | None, pass_count: int) -> int:
    _check_deadline(deadline_s)

    legal_bb = _legal_moves_bitboard(int(player_bits), int(opponent_bits))
    empties = BOARD_CELL_COUNT - _bit_count(int(player_bits) | int(opponent_bits))

    if legal_bb == 0:
        opponent_legal_bb = _legal_moves_bitboard(int(opponent_bits), int(player_bits))
        if opponent_legal_bb == 0:
            return _terminal_score(int(player_bits), int(opponent_bits))
        return -_negamax(cache, int(opponent_bits), int(player_bits), int(depth), -int(beta), -int(alpha), deadline_s, int(pass_count) + 1)

    if empties <= int(cache.exact_threshold):
        return _solve_exact(cache, int(player_bits), int(opponent_bits), int(alpha), int(beta), deadline_s, int(pass_count))

    if int(depth) <= 0:
        return _evaluate(int(player_bits), int(opponent_bits))

    original_alpha = int(alpha)
    key = (int(player_bits), int(opponent_bits))
    tt_entry = cache.transposition.get(key)
    if tt_entry is not None and int(tt_entry.depth) >= int(depth):
        if int(tt_entry.bound) == _BOUND_EXACT:
            return int(tt_entry.score)
        if int(tt_entry.bound) == _BOUND_LOWER:
            alpha = max(int(alpha), int(tt_entry.score))
        elif int(tt_entry.bound) == _BOUND_UPPER:
            beta = min(int(beta), int(tt_entry.score))
        if int(alpha) >= int(beta):
            return int(tt_entry.score)

    best_score = _LOSS_SCORE
    best_move: int | None = None
    for move_index in _ordered_moves(int(player_bits), int(opponent_bits), _bitboard_to_moves(legal_bb), None if tt_entry is None else tt_entry.best_move):
        next_player, next_opponent = _apply_move_bits(int(player_bits), int(opponent_bits), int(move_index))
        score = -_negamax(cache, int(next_opponent), int(next_player), int(depth) - 1, -int(beta), -int(alpha), deadline_s, 0)
        if score > int(best_score):
            best_score = int(score)
            best_move = int(move_index)
        if int(best_score) > int(alpha):
            alpha = int(best_score)
        if int(alpha) >= int(beta):
            break

    bound = _BOUND_EXACT
    if int(best_score) <= int(original_alpha):
        bound = _BOUND_UPPER
    elif int(best_score) >= int(beta):
        bound = _BOUND_LOWER

    cache.transposition[key] = _TranspositionEntry(depth=int(depth), score=int(best_score), bound=int(bound), best_move=best_move)
    return int(best_score)


def choose_insane_move(board: tuple[int, ...] | list[int], side: int, *, random_seed: int=0, time_budget_s: float=4.0, cache: InsaneSearchCache | None=None) -> int | None:
    materialized = coerce_board(board)
    normalized_side = normalize_side(side, default=SIDE_BLACK)
    if normalized_side not in (SIDE_BLACK, SIDE_WHITE):
        return None

    black_bits, white_bits = _bitboards_from_board(materialized)
    if normalized_side == SIDE_BLACK:
        player_bits = int(black_bits)
        opponent_bits = int(white_bits)
    else:
        player_bits = int(white_bits)
        opponent_bits = int(black_bits)

    legal_bb = _legal_moves_bitboard(int(player_bits), int(opponent_bits))
    legal_moves = _bitboard_to_moves(legal_bb)
    if not legal_moves:
        return None

    active_cache = cache or InsaneSearchCache()
    book_moves = tuple(move for move in active_cache.opening_book.moves_for(materialized, normalized_side) if move in set(legal_moves))
    if book_moves:
        chooser = random.Random(int(random_seed))
        return int(chooser.choice(tuple(sorted(int(move) for move in book_moves))))

    deadline = time.perf_counter() + max(0.5, float(time_budget_s))
    empties = BOARD_CELL_COUNT - _bit_count(int(player_bits) | int(opponent_bits))
    if empties <= int(active_cache.exact_threshold):
        best_score = _LOSS_SCORE
        best_moves: list[int] = []
        for move_index in _ordered_moves(int(player_bits), int(opponent_bits), legal_moves, None):
            try:
                next_player, next_opponent = _apply_move_bits(int(player_bits), int(opponent_bits), int(move_index))
                score = -_solve_exact(active_cache, int(next_opponent), int(next_player), _LOSS_SCORE, _WIN_SCORE, deadline, 0)
            except TimeoutError:
                break
            if score > int(best_score):
                best_score = int(score)
                best_moves = [int(move_index)]
            elif score == int(best_score):
                best_moves.append(int(move_index))
        chooser = random.Random(int(random_seed))
        return int(chooser.choice(tuple(sorted(best_moves))))

    best_move = int(legal_moves[0])
    best_score = _LOSS_SCORE
    max_depth = min(24, max(6, empties))

    for depth in range(1, max_depth + 1):
        try:
            _check_deadline(deadline)
        except TimeoutError:
            break
        depth_best_score = _LOSS_SCORE
        depth_best_moves: list[int] = []
        for move_index in _ordered_moves(int(player_bits), int(opponent_bits), legal_moves, None):
            try:
                _check_deadline(deadline)
                next_player, next_opponent = _apply_move_bits(int(player_bits), int(opponent_bits), int(move_index))
                score = -_negamax(active_cache, int(next_opponent), int(next_player), int(depth) - 1, _LOSS_SCORE, _WIN_SCORE, deadline, 0)
            except TimeoutError:
                depth_best_moves = []
                break
            if score > int(depth_best_score):
                depth_best_score = int(score)
                depth_best_moves = [int(move_index)]
            elif score == int(depth_best_score):
                depth_best_moves.append(int(move_index))

        if depth_best_moves:
            chooser = random.Random(int(random_seed))
            best_score = int(depth_best_score)
            best_move = int(chooser.choice(tuple(sorted(depth_best_moves))))

        if abs(int(best_score)) >= int(_WIN_SCORE):
            break

    return int(best_move)
