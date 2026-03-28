# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import json

from ..game.rules import apply_move, create_initial_board, find_legal_moves
from ..game.types import BOARD_CELL_COUNT, SIDE_BLACK, coerce_board, encode_board, normalize_side, other_side

_BOARD_SIZE = 8


def _default_project_root() -> Path:
    """I define P_0 as the repository root inferred from the module path. I use this anchor whenever the caller omits an explicit project root, because user book persistence is rooted in the application workspace rather than in the package tree."""
    return Path(__file__).resolve().parents[6]


def normalize_project_root(project_root: str | Path | None = None) -> Path:
    """I define N_P(x) as the total projection from an optional path-like input onto an absolute project root. I resolve and expand the supplied path when possible and otherwise fall back to P_0 so that persistence code remains total on malformed inputs."""
    if project_root is None:
        return _default_project_root()
    try:
        return Path(project_root).expanduser().resolve()
    except Exception:
        return _default_project_root()


def _project_root_key(project_root: str | Path | None = None) -> str:
    """I define K_P(x) = str(N_P(x)). I use this string key as the cache index for per-project opening-book state."""
    return str(normalize_project_root(project_root))


def _index_to_row_col(index: int) -> tuple[int, int]:
    """I define psi(i) = (floor(i/8), i mod 8) for 0 <= i < 64. This is the canonical affine coordinate chart that I use for symmetry transforms on board indices."""
    idx = int(index)
    return (idx // _BOARD_SIZE, idx % _BOARD_SIZE)


def _row_col_to_index(row: int, col: int) -> int:
    """I define psi^{-1}(r,c) = 8*r + c. Together with psi, this map lets me express dihedral board symmetries through coordinate transforms instead of per-case index tables written by hand."""
    return int(row) * _BOARD_SIZE + int(col)


def _transform_row_col(transform_id: int, row: int, col: int) -> tuple[int, int]:
    """I define T_k(r,c) for k in {0,...,7} as the eight elements of the square-board dihedral action that I actually use for canonicalization. These transforms generate the rotations and reflections needed to identify symmetry-equivalent opening-book positions."""
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
    """I precompute F_k(i) = psi^{-1}(T_k(psi(i))) and its inverse I_k for every symmetry id k. This converts repeated canonicalization from coordinate arithmetic into O(1) table lookup per square."""
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
    """I define F_k(i) as the transformed board index under symmetry k. I reject indices outside [0,63] because canonicalization over an invalid square would be mathematically undefined and would corrupt the book key space."""
    idx = int(index)
    if idx < 0 or idx >= BOARD_CELL_COUNT:
        raise ValueError(f"Square index out of range: {index}")
    return int(_FORWARD_TABLES[int(transform_id) & 7][idx])


def inverse_transform_index(index: int, transform_id: int) -> int:
    """I define I_k(i) as the inverse transformed index under symmetry k. This map satisfies I_k(F_k(i)) = i on the admissible board domain and is required to map canonical book moves back into the caller's coordinate frame."""
    idx = int(index)
    if idx < 0 or idx >= BOARD_CELL_COUNT:
        raise ValueError(f"Square index out of range: {index}")
    return int(_INVERSE_TABLES[int(transform_id) & 7][idx])


def transform_board(board: tuple[int, ...] | list[int], transform_id: int) -> tuple[int, ...]:
    """I define B_k(c)_F_k(i) = c_i for every board cell i. This is the induced action of symmetry k on the full board state, and I use it when computing canonical symmetry representatives."""
    source = coerce_board(board)
    transformed = [0] * BOARD_CELL_COUNT
    forward = _FORWARD_TABLES[int(transform_id) & 7]
    for index, value in enumerate(source):
        transformed[int(forward[index])] = int(value)
    return tuple(transformed)


def canonical_position_key(board: tuple[int, ...] | list[int], side: int) -> tuple[str, int]:
    """I define K(board, side) = min_k(str(side) + ':' + encode(B_k(board))) under lexicographic order, together with the minimizing symmetry id k. This canonical representative collapses all dihedral board symmetries into one cache and opening-book key."""
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
    """I model the opening book as a finite map M : canonical_position_key -> tuple(canonical_move_indices). I store moves in the canonical frame so that symmetry collapse occurs once at load time rather than at every query site."""
    moves_by_key: dict[str, tuple[int, ...]]

    def moves_for(self, board: tuple[int, ...] | list[int], side: int) -> tuple[int, ...]:
        """I define Q(board, side) = I_k(M[K(board,side)]) where k is the minimizing symmetry of the queried position. This returns legal move candidates in the caller's native frame while preserving canonical storage internally."""
        key, transform_id = canonical_position_key(board, side)
        canonical_moves = self.moves_by_key.get(str(key))
        if not canonical_moves:
            return ()
        return tuple(int(inverse_transform_index(move, transform_id)) for move in canonical_moves)


@dataclass(frozen=True)
class OpeningBookSummary:
    """I model a compact cardinality report as Sigma = (bundled_lines, user_lines, total_lines). I use this record in settings UI and commit-level diagnostics because those surfaces require counts, not the full line corpus."""
    bundled_lines: int = 0
    user_lines: int = 0
    total_lines: int = 0


def _bundled_opening_book_resource():
    return files("ludoxel.features.othello.resources").joinpath("opening_book.json")


def user_opening_book_file_path(project_root: str | Path | None = None) -> Path:
    """I define P_u(root) = root/configs/othello_opening_book.json. This location is the mutable user extension of the bundled book and therefore survives application restarts and interrupted learning sessions."""
    return normalize_project_root(project_root) / "configs" / "othello_opening_book.json"


def _normalize_line(raw_line: object) -> tuple[int, ...]:
    """I define N_l(line) as the total validator for one opening line, with codomain tuple([0,63]^n). I reject the entire line if any move lies outside the board index domain because partial repair would silently alter the intended move sequence."""
    if not isinstance(raw_line,(list, tuple)):
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


def _normalize_lines(raw_lines: object) -> tuple[tuple[int, ...], ...]:
    """I define N_L(lines) as sequence normalization plus duplicate elimination with order preservation. This makes serialized line corpora stable under repeated write cycles and idempotent under import merges."""
    if not isinstance(raw_lines,(list, tuple)):
        return ()
    normalized: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for raw_line in raw_lines:
        line = _normalize_line(raw_line)
        if not line or line in seen:
            continue
        seen.add(line)
        normalized.append(line)
    return tuple(normalized)


def _read_lines_from_path(path: Path) -> tuple[tuple[int, ...], ...]:
    """I define R(path) as resilient JSON line loading with schema tolerance for both raw lists and `{lines: ...}` payloads. I return the empty corpus on read or parse failure so that user-book corruption does not crash engine startup."""
    if not path.exists():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ()
    return _read_lines_from_payload(raw)


def _read_lines_from_payload(raw: object) -> tuple[tuple[int, ...], ...]:
    """I define R_payload(raw) as the schema-tolerant normalization map from decoded JSON into the canonical opening-line corpus. This separates transport decoding from structural validation so that packaged resources and filesystem-backed user files follow the same normalization law."""
    if isinstance(raw, list):
        return _normalize_lines(raw)
    if isinstance(raw, dict):
        return _normalize_lines(raw.get("lines",[]))
    return ()


def _write_lines_to_path(path: Path, lines: tuple[tuple[int, ...], ...]) -> None:
    """I define W(path, lines) as deterministic JSON serialization of the normalized line corpus. I always write an explicit version field because this file is application state, not an opaque cache artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "lines": [list(line) for line in tuple(lines)]}
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def _merge_lines(*sources: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    """I define U(L_1,...,L_n) as stable set union with first-occurrence preservation. This lets me compose bundled and user books without losing deterministic ordering semantics in exported files."""
    merged: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for source in sources:
        for line in tuple(source):
            if line in seen:
                continue
            seen.add(line)
            merged.append(tuple(line))
    return tuple(merged)


def _record_line(mapping: dict[str, set[int]], line: tuple[int, ...]) -> None:
    """I define R_line(M, line) as the forward projection of one legal move sequence into the canonical map M. At each ply j, I store the canonical image of line_j under the current board symmetry representative so that the loaded book is indexed by positions rather than by full prefixes only."""
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


def load_bundled_opening_book_lines() -> tuple[tuple[int, ...], ...]:
    """I define L_b as the normalized bundled line corpus. I expose this wrapper so that callers do not touch the cache implementation directly."""
    return _load_bundled_opening_book_lines_cached()


@lru_cache(maxsize=1)
def _load_bundled_opening_book_lines_cached() -> tuple[tuple[int, ...], ...]:
    """I memoize L_b because packaged data is immutable within one process lifetime. This reduces redundant JSON parsing on repeated AI and UI queries."""
    try:
        raw = json.loads(_bundled_opening_book_resource().read_text(encoding="utf-8"))
    except Exception:
        return ()
    return _read_lines_from_payload(raw)


def load_user_opening_book_lines(project_root: str | Path | None = None) -> tuple[tuple[int, ...], ...]:
    """I define L_u(root) as the normalized user-extension corpus stored under the project workspace. I keep the project root explicit because multiple workspaces may coexist within one Python process."""
    return _load_user_opening_book_lines_cached(_project_root_key(project_root))


@lru_cache(maxsize=8)
def _load_user_opening_book_lines_cached(project_root_key: str) -> tuple[tuple[int, ...], ...]:
    """I memoize L_u(root) by normalized project-root key. This keeps repeated analysis cheap while still permitting explicit cache invalidation after import, export, or learning writes."""
    return _read_lines_from_path(user_opening_book_file_path(project_root_key))


def load_opening_book_lines(project_root: str | Path | None = None) -> tuple[tuple[int, ...], ...]:
    """I define L(root) = U(L_b, L_u(root)). This is the complete opening-line corpus visible to search, export, and learning initialization."""
    return _merge_lines(load_bundled_opening_book_lines(), load_user_opening_book_lines(project_root))


def opening_book_summary(project_root: str | Path | None = None) -> OpeningBookSummary:
    """I define Sigma(root) = (|L_b|, |L_u(root)|, |L(root)|). I use these exact cardinalities in the Othello settings UI so that book growth is observable without loading the full search map into presentation code."""
    bundled_lines = load_bundled_opening_book_lines()
    user_lines = load_user_opening_book_lines(project_root)
    merged_lines = _merge_lines(bundled_lines, user_lines)
    return OpeningBookSummary(bundled_lines=len(bundled_lines), user_lines=len(user_lines), total_lines=len(merged_lines))


def save_user_opening_book_lines(lines: tuple[tuple[int, ...], ...] | list[tuple[int, ...]] | list[list[int]], project_root: str | Path | None = None) -> tuple[tuple[int, ...], ...]:
    """I define S_u(root, lines) as persistence of the user-only delta U(lines) \\ L_b. This subtraction is deliberate: I never rewrite bundled data into mutable workspace state, and I therefore preserve a strict separation between shipped content and user-authored extensions."""
    merged_lines = _normalize_lines(list(lines))
    bundled_lines = load_bundled_opening_book_lines()
    bundled_set = set(bundled_lines)
    user_only_lines = tuple(line for line in merged_lines if line not in bundled_set)
    _write_lines_to_path(user_opening_book_file_path(project_root), user_only_lines)
    clear_opening_book_cache(project_root)
    return _merge_lines(bundled_lines, user_only_lines)


def save_opening_book_lines(lines: tuple[tuple[int, ...], ...] | list[tuple[int, ...]] | list[list[int]], project_root: str | Path | None = None) -> tuple[tuple[int, ...], ...]:
    """I define S(root, lines) as the public write entry point for the effective book corpus. Internally I delegate to S_u because only the user delta is mutable."""
    return save_user_opening_book_lines(lines, project_root=project_root)


def import_opening_book_file(import_path: str | Path, *, project_root: str | Path | None = None) -> OpeningBookSummary:
    """I define I(root, path) = Sigma(root) after merging the imported corpus into the effective line set and reserializing the user delta. This operation is union-based and therefore idempotent with respect to repeated imports of the same file."""
    normalized_path = Path(import_path).expanduser().resolve()
    imported_lines = _read_lines_from_path(normalized_path)
    merged_lines = _merge_lines(load_opening_book_lines(project_root), imported_lines)
    save_user_opening_book_lines(merged_lines, project_root=project_root)
    return opening_book_summary(project_root)


def export_opening_book_file(export_path: str | Path, *, project_root: str | Path | None = None) -> Path:
    """I define E(root, path) as serialization of the full effective corpus L(root) into an arbitrary export target. I intentionally export bundled and user lines together because the exported artifact is meant to be a self-contained book snapshot."""
    normalized_path = Path(export_path).expanduser().resolve()
    _write_lines_to_path(normalized_path, load_opening_book_lines(project_root))
    return normalized_path


def clear_opening_book_cache(_project_root: str | Path | None = None) -> None:
    """I invalidate every memoized projection derived from the user and effective opening-book corpora. The root argument is presently ignored because invalidation is global across all cached project keys."""
    _load_user_opening_book_lines_cached.cache_clear()
    _load_opening_book_cached.cache_clear()


def _load_opening_book_from_lines(lines: tuple[tuple[int, ...], ...]) -> OpeningBook:
    """I define M(lines) by replaying every legal line prefix into the canonical move map. This compilation step converts prefix lists into a position-indexed opening book that the engine can query in O(1) expected time per position."""
    mapping: dict[str, set[int]] = {}
    for item in tuple(lines):
        _record_line(mapping, item)
    frozen = {str(key): tuple(sorted(int(move) for move in moves)) for key, moves in mapping.items() if moves}
    return OpeningBook(moves_by_key=frozen)


def load_opening_book(project_root: str | Path | None = None) -> OpeningBook:
    """I define B(root) = M(L(root)). This is the effective search-time opening book visible to the engine for one workspace."""
    return _load_opening_book_cached(_project_root_key(project_root))


@lru_cache(maxsize=8)
def _load_opening_book_cached(project_root_key: str) -> OpeningBook:
    """I memoize B(root) by normalized project-root key because opening-book compilation is deterministic and potentially reused by repeated search requests. I clear this cache explicitly after every mutation of user book state."""
    return _load_opening_book_from_lines(load_opening_book_lines(project_root_key))
