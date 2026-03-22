# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import json

from .rules import apply_move, create_initial_board, find_legal_moves
from .types import BOARD_CELL_COUNT, SIDE_BLACK, coerce_board, encode_board, normalize_side, other_side

_BOARD_SIZE = 8


def _index_to_row_col(index: int) -> tuple[int, int]:
    idx = int(index)
    return (idx // _BOARD_SIZE, idx % _BOARD_SIZE)


def _row_col_to_index(row: int, col: int) -> int:
    return int(row) * _BOARD_SIZE + int(col)


def _transform_row_col(transform_id: int, row: int, col: int) -> tuple[int, int]:
    tid = int(transform_id) & 7
    r = int(row)
    c = int(col)
    if tid == 0:
        return (r, c)
    if tid == 1:
        return (c, _BOARD_SIZE - 1 - r)
    if tid == 2:
        return (_BOARD_SIZE - 1 - r, _BOARD_SIZE - 1 - c)
    if tid == 3:
        return (_BOARD_SIZE - 1 - c, r)
    if tid == 4:
        return (r, _BOARD_SIZE - 1 - c)
    if tid == 5:
        return (_BOARD_SIZE - 1 - c, _BOARD_SIZE - 1 - r)
    if tid == 6:
        return (_BOARD_SIZE - 1 - r, c)
    return (c, r)


def _build_transform_tables() -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    forward_tables: list[tuple[int, ...]] = []
    inverse_tables: list[tuple[int, ...]] = []

    for transform_id in range(8):
        forward = [0] * BOARD_CELL_COUNT
        inverse = [0] * BOARD_CELL_COUNT
        for index in range(BOARD_CELL_COUNT):
            row, col = _index_to_row_col(index)
            next_row, next_col = _transform_row_col(transform_id, row, col)
            next_index = _row_col_to_index(next_row, next_col)
            forward[index] = int(next_index)
            inverse[next_index] = int(index)
        forward_tables.append(tuple(forward))
        inverse_tables.append(tuple(inverse))

    return (tuple(forward_tables), tuple(inverse_tables))


_FORWARD_TABLES, _INVERSE_TABLES = _build_transform_tables()


def transform_index(index: int, transform_id: int) -> int:
    idx = int(index)
    if idx < 0 or idx >= BOARD_CELL_COUNT:
        raise ValueError(f"Square index out of range: {index}")
    return int(_FORWARD_TABLES[int(transform_id) & 7][idx])


def inverse_transform_index(index: int, transform_id: int) -> int:
    idx = int(index)
    if idx < 0 or idx >= BOARD_CELL_COUNT:
        raise ValueError(f"Square index out of range: {index}")
    return int(_INVERSE_TABLES[int(transform_id) & 7][idx])


def transform_board(board: tuple[int, ...] | list[int], transform_id: int) -> tuple[int, ...]:
    source = coerce_board(board)
    transformed = [0] * BOARD_CELL_COUNT
    forward = _FORWARD_TABLES[int(transform_id) & 7]
    for index, value in enumerate(source):
        transformed[int(forward[index])] = int(value)
    return tuple(transformed)


def canonical_position_key(board: tuple[int, ...] | list[int], side: int) -> tuple[str, int]:
    source = coerce_board(board)
    normalized_side = normalize_side(side, default=SIDE_BLACK)

    best_key = ""
    best_transform = 0
    first = True

    for transform_id in range(8):
        transformed = transform_board(source, int(transform_id))
        key = f"{int(normalized_side)}:{encode_board(transformed)}"
        if first or key < best_key:
            best_key = str(key)
            best_transform = int(transform_id)
            first = False

    return (str(best_key), int(best_transform))


@dataclass(frozen=True)
class OpeningBook:
    moves_by_key: dict[str, tuple[int, ...]]

    def moves_for(self, board: tuple[int, ...] | list[int], side: int) -> tuple[int, ...]:
        key, transform_id = canonical_position_key(board, side)
        canonical_moves = self.moves_by_key.get(str(key))
        if not canonical_moves:
            return ()
        return tuple(int(inverse_transform_index(move, transform_id)) for move in canonical_moves)


def _book_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "opening_book.json"


def _normalize_line(raw_line: object) -> tuple[int, ...]:
    if not isinstance(raw_line, list):
        return ()
    out: list[int] = []
    for value in raw_line:
        try:
            index = int(value)
        except Exception:
            return ()
        if index < 0 or index >= BOARD_CELL_COUNT:
            return ()
        out.append(int(index))
    return tuple(out)


def _record_line(mapping: dict[str, set[int]], line: tuple[int, ...]) -> None:
    if not line:
        return

    board = create_initial_board()
    side_to_move = SIDE_BLACK

    for move_index in line:
        legal_moves = tuple(int(index) for index in find_legal_moves(board, side_to_move))
        if int(move_index) not in set(legal_moves):
            return

        key, transform_id = canonical_position_key(board, side_to_move)
        bucket = mapping.setdefault(str(key), set())
        bucket.add(int(transform_index(int(move_index), int(transform_id))))

        board, _flipped = apply_move(board, side=side_to_move, index=int(move_index))
        side_to_move = other_side(side_to_move)

        if not find_legal_moves(board, side_to_move):
            other = other_side(side_to_move)
            if find_legal_moves(board, other):
                side_to_move = other


def _load_opening_book_from_disk() -> OpeningBook:
    path = _book_file_path()
    if not path.exists():
        return OpeningBook(moves_by_key={})

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return OpeningBook(moves_by_key={})

    lines_raw = raw.get("lines",[])
    if not isinstance(lines_raw, list):
        return OpeningBook(moves_by_key={})

    mapping: dict[str, set[int]] = {}
    for item in lines_raw:
        _record_line(mapping, _normalize_line(item))

    frozen = {str(key): tuple(sorted(int(move) for move in moves)) for key, moves in mapping.items() if moves}
    return OpeningBook(moves_by_key=frozen)


@lru_cache(maxsize=1)
def load_opening_book() -> OpeningBook:
    return _load_opening_book_from_disk()
