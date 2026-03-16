# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/othello/rules.py
from __future__ import annotations

from .board import BOARD_SIZE, row_col_to_square_index, square_index_to_row_col
from .types import BOARD_CELL_COUNT, OTHELLO_WINNER_DRAW, SIDE_BLACK, SIDE_EMPTY, SIDE_WHITE, normalize_side, other_side
_DIRECTIONS: tuple[tuple[int, int], ...] = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def row_col_to_index(row: int, col: int) -> int:
    return row_col_to_square_index(row, col)


def index_to_row_col(index: int) -> tuple[int, int]:
    return square_index_to_row_col(index)


def create_initial_board() -> tuple[int, ...]:
    board = [SIDE_EMPTY] * BOARD_CELL_COUNT
    board[row_col_to_index(3, 3)] = SIDE_WHITE
    board[row_col_to_index(3, 4)] = SIDE_BLACK
    board[row_col_to_index(4, 3)] = SIDE_BLACK
    board[row_col_to_index(4, 4)] = SIDE_WHITE
    return tuple(board)


def counts_for_board(board: tuple[int, ...] | list[int]) -> tuple[int, int]:
    black = 0
    white = 0
    for value in tuple(board)[:BOARD_CELL_COUNT]:
        side = normalize_side(value)
        if side == SIDE_BLACK:
            black += 1
        elif side == SIDE_WHITE:
            white += 1
    return (int(black), int(white))


def _captures_in_direction(board: tuple[int, ...], *, side: int, row: int, col: int, d_row: int, d_col: int) -> tuple[int, ...]:
    enemy = other_side(side)
    if enemy == SIDE_EMPTY:
        return ()

    captures: list[int] = []
    cur_row = int(row) + int(d_row)
    cur_col = int(col) + int(d_col)

    while 0 <= cur_row < BOARD_SIZE and 0 <= cur_col < BOARD_SIZE:
        index = row_col_to_index(cur_row, cur_col)
        current = normalize_side(board[index])
        if current == enemy:
            captures.append(index)
            cur_row += int(d_row)
            cur_col += int(d_col)
            continue
        if current == side and captures:
            return tuple(captures)
        return ()

    return ()


def captures_for_move(board: tuple[int, ...] | list[int], *, side: int, index: int) -> tuple[int, ...]:
    norm_side = normalize_side(side)
    if norm_side not in (SIDE_BLACK, SIDE_WHITE):
        return ()

    idx = int(index)
    if idx < 0 or idx >= BOARD_CELL_COUNT:
        return ()

    materialized = tuple(normalize_side(value) for value in tuple(board)[:BOARD_CELL_COUNT])
    if len(materialized) < BOARD_CELL_COUNT:
        materialized = tuple(materialized) + tuple([SIDE_EMPTY] * (BOARD_CELL_COUNT - len(materialized)))

    if materialized[idx] != SIDE_EMPTY:
        return ()

    row, col = index_to_row_col(idx)
    captured: list[int] = []
    for d_row, d_col in _DIRECTIONS:
        captured.extend(_captures_in_direction(materialized, side=norm_side, row=row, col=col, d_row=d_row, d_col=d_col))
    return tuple(captured)


def find_legal_moves(board: tuple[int, ...] | list[int], side: int) -> tuple[int, ...]:
    materialized = tuple(normalize_side(value) for value in tuple(board)[:BOARD_CELL_COUNT])
    if len(materialized) < BOARD_CELL_COUNT:
        materialized = tuple(materialized) + tuple([SIDE_EMPTY] * (BOARD_CELL_COUNT - len(materialized)))

    legal: list[int] = []
    for index in range(BOARD_CELL_COUNT):
        if materialized[index] != SIDE_EMPTY:
            continue
        if captures_for_move(materialized, side=side, index=index):
            legal.append(index)
    return tuple(legal)


def has_any_legal_move(board: tuple[int, ...] | list[int], side: int) -> bool:
    return len(find_legal_moves(board, side)) > 0


def apply_move(board: tuple[int, ...] | list[int], *, side: int, index: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    captured = captures_for_move(board, side=side, index=index)
    if not captured:
        raise ValueError("The requested Othello move is illegal because it flips no opposing discs.")

    materialized = list(tuple(normalize_side(value) for value in tuple(board)[:BOARD_CELL_COUNT]))
    while len(materialized) < BOARD_CELL_COUNT:
        materialized.append(SIDE_EMPTY)

    move_index = int(index)
    materialized[move_index] = normalize_side(side)
    for captured_index in captured:
        materialized[int(captured_index)] = normalize_side(side)
    return (tuple(materialized[:BOARD_CELL_COUNT]), tuple(captured))


def winner_for_board(board: tuple[int, ...] | list[int]) -> str:
    black, white = counts_for_board(board)
    if black > white:
        return "black"
    if white > black:
        return "white"
    return OTHELLO_WINNER_DRAW
