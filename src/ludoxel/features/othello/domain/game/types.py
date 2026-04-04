# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .....shared.math.scalars import clampf, clampi, coerce_clampf, coerce_clampi

SIDE_EMPTY: int = 0
SIDE_BLACK: int = 1
SIDE_WHITE: int = 2

_SIDE_TOKENS: dict[int, str] = {SIDE_EMPTY: ".", SIDE_BLACK: "B", SIDE_WHITE: "W"}
_TOKEN_SIDES: dict[str, int] = {value: key for key, value in _SIDE_TOKENS.items()}

OTHELLO_DIFFICULTY_WEAK: str = "weak"
OTHELLO_DIFFICULTY_MEDIUM: str = "medium"
OTHELLO_DIFFICULTY_STRONG: str = "strong"
OTHELLO_DIFFICULTY_INSANE: str = "insane"
OTHELLO_DIFFICULTY_INSANE_PLUS: str = "insane_plus"
OTHELLO_DIFFICULTIES: tuple[str, ...] = (OTHELLO_DIFFICULTY_WEAK, OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_STRONG, OTHELLO_DIFFICULTY_INSANE, OTHELLO_DIFFICULTY_INSANE_PLUS)

OTHELLO_TIME_CONTROL_OFF: str = "off"
OTHELLO_TIME_CONTROL_PER_MOVE_5S: str = "per_move_5s"
OTHELLO_TIME_CONTROL_PER_MOVE_10S: str = "per_move_10s"
OTHELLO_TIME_CONTROL_PER_MOVE_30S: str = "per_move_30s"
OTHELLO_TIME_CONTROL_PER_SIDE_1M: str = "per_side_1m"
OTHELLO_TIME_CONTROL_PER_SIDE_3M: str = "per_side_3m"
OTHELLO_TIME_CONTROL_PER_SIDE_5M: str = "per_side_5m"
OTHELLO_TIME_CONTROL_PER_SIDE_10M: str = "per_side_10m"
OTHELLO_TIME_CONTROL_PER_SIDE_20M: str = "per_side_20m"
OTHELLO_TIME_CONTROL_NONE: str = OTHELLO_TIME_CONTROL_OFF
OTHELLO_TIME_CONTROLS: tuple[str, ...] = (OTHELLO_TIME_CONTROL_OFF, OTHELLO_TIME_CONTROL_PER_MOVE_5S, OTHELLO_TIME_CONTROL_PER_MOVE_10S, OTHELLO_TIME_CONTROL_PER_MOVE_30S, OTHELLO_TIME_CONTROL_PER_SIDE_1M, OTHELLO_TIME_CONTROL_PER_SIDE_3M, OTHELLO_TIME_CONTROL_PER_SIDE_5M, OTHELLO_TIME_CONTROL_PER_SIDE_10M, OTHELLO_TIME_CONTROL_PER_SIDE_20M)
_TIME_CONTROL_LIMITS_S: dict[str, float | None] = {OTHELLO_TIME_CONTROL_OFF: None, OTHELLO_TIME_CONTROL_PER_MOVE_5S: 5.0, OTHELLO_TIME_CONTROL_PER_MOVE_10S: 10.0, OTHELLO_TIME_CONTROL_PER_MOVE_30S: 30.0, OTHELLO_TIME_CONTROL_PER_SIDE_1M: 60.0, OTHELLO_TIME_CONTROL_PER_SIDE_3M: 180.0, OTHELLO_TIME_CONTROL_PER_SIDE_5M: 300.0, OTHELLO_TIME_CONTROL_PER_SIDE_10M: 600.0, OTHELLO_TIME_CONTROL_PER_SIDE_20M: 1200.0}
_PER_MOVE_TIME_CONTROLS: tuple[str, ...] = (OTHELLO_TIME_CONTROL_PER_MOVE_5S, OTHELLO_TIME_CONTROL_PER_MOVE_10S, OTHELLO_TIME_CONTROL_PER_MOVE_30S)

OTHELLO_ANIMATION_OFF: str = "off"
OTHELLO_ANIMATION_FAST: str = "fast"
OTHELLO_ANIMATION_SLOW: str = "slow"
OTHELLO_ANIMATION_MODES: tuple[str, ...] = (OTHELLO_ANIMATION_OFF, OTHELLO_ANIMATION_FAST, OTHELLO_ANIMATION_SLOW)

OTHELLO_GAME_STATE_IDLE: str = "idle"
OTHELLO_GAME_STATE_PLAYER_TURN: str = "player_turn"
OTHELLO_GAME_STATE_AI_TURN: str = "ai_turn"
OTHELLO_GAME_STATE_ANIMATING: str = "animating"
OTHELLO_GAME_STATE_FINISHED: str = "finished"
OTHELLO_GAME_STATUSES: tuple[str, ...] = (OTHELLO_GAME_STATE_IDLE, OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_GAME_STATE_AI_TURN, OTHELLO_GAME_STATE_ANIMATING, OTHELLO_GAME_STATE_FINISHED)

OTHELLO_WINNER_DRAW: str = "draw"

DEFAULT_TIME_LIMIT_S: float = 20.0 * 60.0
BOARD_CELL_COUNT: int = 64
OTHELLO_AI_THREAD_MIN: int = 1
OTHELLO_AI_THREAD_MAX: int = 8
OTHELLO_AI_HASH_LEVEL_MIN: int = 0
OTHELLO_AI_HASH_LEVEL_MAX: int = 6
OTHELLO_AI_SACRIFICE_LEVEL_MIN: int = 0
OTHELLO_AI_SACRIFICE_LEVEL_MAX: int = 4
OTHELLO_BOOK_LEARNING_DEPTH_MIN: int = 0
OTHELLO_BOOK_LEARNING_DEPTH_MAX: int = 60
DEFAULT_OTHELLO_THREAD_COUNT: int = 1
DEFAULT_OTHELLO_HASH_LEVEL: int = 2
DEFAULT_OTHELLO_SACRIFICE_LEVEL: int = 2
DEFAULT_OTHELLO_BOOK_LEARNING_DEPTH: int = 55
DEFAULT_OTHELLO_BOOK_PER_MOVE_ERROR: float = 22.0
DEFAULT_OTHELLO_BOOK_CUMULATIVE_ERROR: float = 19.0
DEFAULT_OTHELLO_BOOK_LEAF_ERROR: float = 20.0
OTHELLO_BOOK_ERROR_MIN: float = 0.0
OTHELLO_BOOK_ERROR_MAX: float = 24.0


def _default_initial_board() -> tuple[int, ...]:
    board = [SIDE_EMPTY] * BOARD_CELL_COUNT
    board[3 * 8 + 3] = SIDE_WHITE
    board[3 * 8 + 4] = SIDE_BLACK
    board[4 * 8 + 3] = SIDE_BLACK
    board[4 * 8 + 4] = SIDE_WHITE
    return tuple(board)


def normalize_side(value: object, *, default: int = SIDE_EMPTY) -> int:
    """I define N_s(x) in {0,1,2} as the canonical side normalizer with the encoding 0 = empty, 1 = black, and 2 = white. I first resolve string aliases through a finite lexical map, I then coerce numerically when lexical resolution is absent, and I finally return the designated fallback whenever x is not admissible in the state space of a disc side."""
    if isinstance(value, str):
        raw = str(value).strip().lower()
        if raw in ("black", "player_first", "first", "b"):
            return SIDE_BLACK
        if raw in ("white", "player_second", "second", "w"):
            return SIDE_WHITE
        if raw in ("empty", ".", "none", ""):
            return SIDE_EMPTY

    try:
        side = int(value)
    except Exception:
        side = int(default)

    if side in (SIDE_EMPTY, SIDE_BLACK, SIDE_WHITE):
        return side
    fallback = int(default)
    if fallback in (SIDE_EMPTY, SIDE_BLACK, SIDE_WHITE):
        return fallback
    return SIDE_EMPTY


def other_side(side: int) -> int:
    """I define O(s) by O(1) = 2, O(2) = 1, and O(0) = 0. This involution satisfies O(O(s)) = s for s in {1,2} and preserves the empty element as a fixed point."""
    norm = normalize_side(side, default=SIDE_EMPTY)
    if norm == SIDE_BLACK:
        return SIDE_WHITE
    if norm == SIDE_WHITE:
        return SIDE_BLACK
    return SIDE_EMPTY


def normalize_player_side(value: object, *, default: int = SIDE_BLACK) -> int:
    """I define N_p(x) = N_s(x) with the additional constraint N_p(x) != 0. Whenever the raw value collapses to the empty side, I project it onto the designated player-side fallback so that turn assignment and AI-side derivation remain total."""
    side = normalize_side(value, default=default)
    if side == SIDE_EMPTY:
        return SIDE_BLACK if int(default) == SIDE_EMPTY else normalize_side(default, default=SIDE_BLACK)
    return side


def normalize_difficulty(value: object, *, default: str = OTHELLO_DIFFICULTY_MEDIUM) -> str:
    """I define N_d(x) in D, where D is the finite difficulty alphabet of the Othello engine. I lower-case and trim the raw token, accept it iff it lies in D, and otherwise return the designated fallback or the canonical medium mode."""
    raw = str(value).strip().lower()
    if raw in OTHELLO_DIFFICULTIES:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_DIFFICULTIES:
        return fallback
    return OTHELLO_DIFFICULTY_MEDIUM


def difficulty_display_name(value: object) -> str:
    """I define L_d : D -> HumanReadable by a total label map over the normalized difficulty domain. This projection is presentation-only and does not alter the underlying engine mode."""
    normalized = normalize_difficulty(value)
    if normalized == OTHELLO_DIFFICULTY_WEAK:
        return "Weak"
    if normalized == OTHELLO_DIFFICULTY_MEDIUM:
        return "Medium"
    if normalized == OTHELLO_DIFFICULTY_STRONG:
        return "Strong"
    if normalized == OTHELLO_DIFFICULTY_INSANE:
        return "Insane"
    if normalized == OTHELLO_DIFFICULTY_INSANE_PLUS:
        return "Insane+"
    return "Medium"


def normalize_time_control(value: object, *, default: str = OTHELLO_TIME_CONTROL_PER_SIDE_20M) -> str:
    """I define N_t(x) in T, where T is the finite set of supported timer modes. I resolve legacy aliases such as `none` and `unlimited` into `off`, then I accept only canonical members of T so that persistence and UI binding operate over a single stable identifier set."""
    raw = str(value).strip().lower()
    if raw in ("no_limit", "unlimited", "none"):
        raw = OTHELLO_TIME_CONTROL_OFF
    if raw in OTHELLO_TIME_CONTROLS:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_TIME_CONTROLS:
        return fallback
    return OTHELLO_TIME_CONTROL_PER_SIDE_20M


def time_control_limit_s(value: object) -> float | None:
    """I define tau(t) as the nominal limit in seconds associated with a normalized timer mode t. I return None exactly for the timer-off state and a finite positive scalar for every bounded per-move or per-side mode."""
    return _TIME_CONTROL_LIMITS_S.get(normalize_time_control(value), float(DEFAULT_TIME_LIMIT_S))


def time_control_is_per_move(value: object) -> bool:
    """I define chi_move(t) = 1 iff the normalized timer mode is constrained per move rather than per side. I use this predicate at turn transition so that only the active side clock is reloaded in sudden-death move-timer modes."""
    return normalize_time_control(value) in _PER_MOVE_TIME_CONTROLS


def time_control_display_name(value: object) -> str:
    """I define L_t : T -> HumanReadable by a total presentation map over the canonical timer domain. This map is deliberately non-invertible at the UI layer because serialization remains governed by the canonical identifiers rather than by labels."""
    normalized = normalize_time_control(value)
    if normalized == OTHELLO_TIME_CONTROL_OFF:
        return "Timer off"
    if normalized == OTHELLO_TIME_CONTROL_PER_MOVE_5S:
        return "5 seconds per move"
    if normalized == OTHELLO_TIME_CONTROL_PER_MOVE_10S:
        return "10 seconds per move"
    if normalized == OTHELLO_TIME_CONTROL_PER_MOVE_30S:
        return "30 seconds per move"
    if normalized == OTHELLO_TIME_CONTROL_PER_SIDE_1M:
        return "1 minute per side"
    if normalized == OTHELLO_TIME_CONTROL_PER_SIDE_3M:
        return "3 minutes per side"
    if normalized == OTHELLO_TIME_CONTROL_PER_SIDE_5M:
        return "5 minutes per side"
    if normalized == OTHELLO_TIME_CONTROL_PER_SIDE_10M:
        return "10 minutes per side"
    return "20 minutes per side"


def normalize_animation_mode(value: object, *, default: str = OTHELLO_ANIMATION_OFF) -> str:
    """I define N_a(x) in A, where A = {off, fast, slow} is the animation-mode alphabet. I collapse legacy disabled-state spellings onto `off` and reject every value outside A so that rendered flip timing remains formally well-defined."""
    raw = str(value).strip().lower()
    if raw in ("none", "disabled", "simultaneous"):
        raw = OTHELLO_ANIMATION_OFF
    if raw in OTHELLO_ANIMATION_MODES:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_ANIMATION_MODES:
        return fallback
    return OTHELLO_ANIMATION_OFF


def animation_mode_display_name(value: object) -> str:
    """I define L_a : A -> HumanReadable by a total label map over animation modes. I keep this projection separate from N_a so that storage and presentation remain decoupled."""
    normalized = normalize_animation_mode(value)
    if normalized == OTHELLO_ANIMATION_SLOW:
        return "Ripple slow"
    if normalized == OTHELLO_ANIMATION_FAST:
        return "Ripple fast"
    return "Animation off"


def normalize_game_status(value: object, *, default: str = OTHELLO_GAME_STATE_IDLE) -> str:
    """I define N_g(x) in G, where G is the finite match-status alphabet. I admit only canonical lifecycle states so that controller transitions, persistence, and HUD composition share one exact status lattice."""
    raw = str(value).strip().lower()
    if raw in OTHELLO_GAME_STATUSES:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_GAME_STATUSES:
        return fallback
    return OTHELLO_GAME_STATE_IDLE


def normalize_thread_count(value: object, *, default: int = DEFAULT_OTHELLO_THREAD_COUNT) -> int:
    """I define N_w(x) = clamp(int(x), w_min, w_max) with total fallback semantics. This projection bounds worker-count configuration inside the process-management envelope supported by the current engine."""
    return coerce_clampi(value, default=int(default), lo=int(OTHELLO_AI_THREAD_MIN), hi=int(OTHELLO_AI_THREAD_MAX))


def normalize_hash_level(value: object, *, default: int = DEFAULT_OTHELLO_HASH_LEVEL) -> int:
    """I define N_h(x) = clamp(int(x), h_min, h_max) with total fallback semantics. I use this bounded integer to control transposition-table capacity without permitting unbounded memory growth through persisted configuration."""
    return coerce_clampi(value, default=int(default), lo=int(OTHELLO_AI_HASH_LEVEL_MIN), hi=int(OTHELLO_AI_HASH_LEVEL_MAX))


def normalize_sacrifice_level(value: object, *, default: int = DEFAULT_OTHELLO_SACRIFICE_LEVEL) -> int:
    """I define N_q(x) = clamp(int(x), q_min, q_max) for the sacrifice-profile selector. This integer is later mapped into evaluation weights and therefore must remain inside the calibrated profile family."""
    return coerce_clampi(value, default=int(default), lo=int(OTHELLO_AI_SACRIFICE_LEVEL_MIN), hi=int(OTHELLO_AI_SACRIFICE_LEVEL_MAX))


def normalize_book_learning_depth(value: object, *, default: int = DEFAULT_OTHELLO_BOOK_LEARNING_DEPTH) -> int:
    """I define N_b(x) = clamp(int(x), d_min, d_max) for opening-book learning depth. I impose this bound to preserve a finite and explicitly calibrated search horizon for offline line expansion."""
    return coerce_clampi(value, default=int(default), lo=int(OTHELLO_BOOK_LEARNING_DEPTH_MIN), hi=int(OTHELLO_BOOK_LEARNING_DEPTH_MAX))


def normalize_book_error(value: object, *, default: float) -> float:
    """I define N_e(x) = clamp(float(x), e_min, e_max) for error thresholds used by book learning, with e_min = 0 and e_max = 24. I impose this bounded interval because the learning UI and persistence model both operate on a deliberately calibrated finite error domain rather than on an unbounded real line."""
    return coerce_clampf(value, default=float(default), lo=float(OTHELLO_BOOK_ERROR_MIN), hi=float(OTHELLO_BOOK_ERROR_MAX))


def side_name(side: int) -> str:
    """I define L_s : {0,1,2} -> {empty,black,white} as the canonical textual projection of a normalized side token. I use this map in persistence payloads and message generation so that external state remains semantically explicit."""
    norm = normalize_side(side, default=SIDE_EMPTY)
    if norm == SIDE_BLACK:
        return "black"
    if norm == SIDE_WHITE:
        return "white"
    return "empty"


def decode_board(raw: object) -> tuple[int, ...]:
    """I define B_decode(text) = (c_0,...,c_63), where each c_i lies in {0,1,2}. I decode the first 64 glyphs through the token alphabet {'.','B','W'} and pad the suffix with empties so that the board representation is always total on 64 cells."""
    text = str(raw or "")
    cells: list[int] = []
    for token in text[:BOARD_CELL_COUNT]:
        cells.append(int(_TOKEN_SIDES.get(str(token).upper(), SIDE_EMPTY)))
    while len(cells) < BOARD_CELL_COUNT:
        cells.append(SIDE_EMPTY)
    return tuple(cells[:BOARD_CELL_COUNT])


def coerce_board(board: object) -> tuple[int, ...]:
    """I define B_coerce(x) as the total projection of an arbitrary iterable or serialized board token onto a 64-cell tuple over {0,1,2}. I preserve the first 64 cells after per-cell side normalization and fill every missing suffix coordinate with the empty side."""
    if isinstance(board, str):
        return decode_board(board)

    try:
        raw = tuple(board)
    except Exception:
        return tuple([SIDE_EMPTY] * BOARD_CELL_COUNT)

    cells: list[int] = []
    for value in raw[:BOARD_CELL_COUNT]:
        cells.append(normalize_side(value))

    while len(cells) < BOARD_CELL_COUNT:
        cells.append(SIDE_EMPTY)

    return tuple(cells[:BOARD_CELL_COUNT])


def encode_board(board: tuple[int, ...] | list[int]) -> str:
    """I define B_encode((c_i)_{i=0}^{63}) = t_0 ... t_63 with t_i in {'.','B','W'}. This is the left inverse of the normalized decoding map over the canonical board domain."""
    cells: list[str] = []
    for side in coerce_board(board):
        cells.append(_SIDE_TOKENS[side])
    return "".join(cells)


@dataclass(frozen=True)
class OthelloSettings:
    """I model the persistent match-configuration vector as S = (d,t,a,p,q,w,h,bd,be_m,be_c,be_l). Each projection is normalized onto a finite admissible domain so that game-state construction, UI binding, and persistence all operate on one canonical parameter manifold."""
    difficulty: str = OTHELLO_DIFFICULTY_MEDIUM
    time_control: str = OTHELLO_TIME_CONTROL_PER_SIDE_20M
    animation_mode: str = OTHELLO_ANIMATION_OFF
    player_side: int = SIDE_BLACK
    sacrifice_level: int = DEFAULT_OTHELLO_SACRIFICE_LEVEL
    thread_count: int = DEFAULT_OTHELLO_THREAD_COUNT
    hash_level: int = DEFAULT_OTHELLO_HASH_LEVEL
    book_learning_depth: int = DEFAULT_OTHELLO_BOOK_LEARNING_DEPTH
    book_per_move_error: float = DEFAULT_OTHELLO_BOOK_PER_MOVE_ERROR
    book_cumulative_error: float = DEFAULT_OTHELLO_BOOK_CUMULATIVE_ERROR
    book_leaf_error: float = DEFAULT_OTHELLO_BOOK_LEAF_ERROR

    def normalized(self) -> "OthelloSettings":
        """I define N_S(S_raw) by componentwise normalization over every field of the settings vector. The result is idempotent, that is, N_S(N_S(S)) = N_S(S), which I rely on throughout persistence and controller code."""
        return OthelloSettings(difficulty=normalize_difficulty(self.difficulty), time_control=normalize_time_control(self.time_control), animation_mode=normalize_animation_mode(self.animation_mode), player_side=normalize_player_side(self.player_side), sacrifice_level=normalize_sacrifice_level(self.sacrifice_level), thread_count=normalize_thread_count(self.thread_count), hash_level=normalize_hash_level(self.hash_level), book_learning_depth=normalize_book_learning_depth(self.book_learning_depth), book_per_move_error=normalize_book_error(self.book_per_move_error, default=float(DEFAULT_OTHELLO_BOOK_PER_MOVE_ERROR)), book_cumulative_error=normalize_book_error(self.book_cumulative_error, default=float(DEFAULT_OTHELLO_BOOK_CUMULATIVE_ERROR)), book_leaf_error=normalize_book_error(self.book_leaf_error, default=float(DEFAULT_OTHELLO_BOOK_LEAF_ERROR)))

    def default_time_limit_s(self) -> float | None:
        """I define tau(S) = tau(S.time_control). This projection extracts the nominal timer horizon associated with the stored match settings without duplicating timer-mode logic in callers."""
        return time_control_limit_s(self.time_control)

    def to_dict(self) -> dict[str, Any]:
        """I define phi_S : S -> JSONMap by serializing the normalized settings vector into stable scalar fields. I serialize semantic identifiers rather than UI labels so that state files remain invariant under presentation changes."""
        normalized = self.normalized()
        return {"difficulty": str(normalized.difficulty), "time_control": str(normalized.time_control), "animation_mode": str(normalized.animation_mode), "player_side": str(side_name(normalized.player_side)), "sacrifice_level": int(normalized.sacrifice_level), "thread_count": int(normalized.thread_count), "hash_level": int(normalized.hash_level), "book_learning_depth": int(normalized.book_learning_depth), "book_per_move_error": float(normalized.book_per_move_error), "book_cumulative_error": float(normalized.book_cumulative_error), "book_leaf_error": float(normalized.book_leaf_error)}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OthelloSettings":
        """I define phi_S^{-1} in the weak engineering sense of total deserialization from an untrusted mapping into the canonical settings domain. Every component is normalized independently so that malformed or partial payloads degrade into valid defaults rather than into undefined state."""
        if not isinstance(data, dict):
            return OthelloSettings()
        return OthelloSettings(difficulty=normalize_difficulty(data.get("difficulty", OTHELLO_DIFFICULTY_MEDIUM)), time_control=normalize_time_control(data.get("time_control", OTHELLO_TIME_CONTROL_PER_SIDE_20M)), animation_mode=normalize_animation_mode(data.get("animation_mode", OTHELLO_ANIMATION_OFF)), player_side=normalize_player_side(data.get("player_side", SIDE_BLACK)), sacrifice_level=normalize_sacrifice_level(data.get("sacrifice_level", DEFAULT_OTHELLO_SACRIFICE_LEVEL)), thread_count=normalize_thread_count(data.get("thread_count", DEFAULT_OTHELLO_THREAD_COUNT)), hash_level=normalize_hash_level(data.get("hash_level", DEFAULT_OTHELLO_HASH_LEVEL)), book_learning_depth=normalize_book_learning_depth(data.get("book_learning_depth", DEFAULT_OTHELLO_BOOK_LEARNING_DEPTH)), book_per_move_error=normalize_book_error(data.get("book_per_move_error", DEFAULT_OTHELLO_BOOK_PER_MOVE_ERROR), default=float(DEFAULT_OTHELLO_BOOK_PER_MOVE_ERROR)), book_cumulative_error=normalize_book_error(data.get("book_cumulative_error", DEFAULT_OTHELLO_BOOK_CUMULATIVE_ERROR), default=float(DEFAULT_OTHELLO_BOOK_CUMULATIVE_ERROR)), book_leaf_error=normalize_book_error(data.get("book_leaf_error", DEFAULT_OTHELLO_BOOK_LEAF_ERROR), default=float(DEFAULT_OTHELLO_BOOK_LEAF_ERROR)))


@dataclass(frozen=True)
class OthelloDepthSample:
    """I model one scalar sample of iterative search as sigma = (depth, score, solved). I preserve this tuple as the minimal unit needed to reconstruct monotone depth traces in the HUD."""
    depth: int
    score: float
    solved: bool = False

    def normalized(self) -> "OthelloDepthSample":
        """I define N_sigma(sigma) by clamping depth to Z_{>=0}, coercing score into R, and boolean-normalizing the solved flag. I use this map to make stored search traces algebraically total."""
        return OthelloDepthSample(depth=max(0, int(self.depth)), score=float(self.score), solved=bool(self.solved))


@dataclass(frozen=True)
class OthelloAnalysis:
    """I model one analysis snapshot as A = (side, best_move, line, score, solved, depth, samples). This object is the exact information surface that I expose from search into HUD composition and AI explanation."""
    side_to_move: int = SIDE_BLACK
    best_move_index: int | None = None
    best_line: tuple[int, ...] = ()
    score: float = 0.0
    solved: bool = False
    depth_reached: int = 0
    depth_samples: tuple[OthelloDepthSample, ...] = ()

    def normalized(self) -> "OthelloAnalysis":
        """I define N_A(A_raw) by normalizing the side token, clamping the best move into [0,63] when present, filtering the principal variation onto legal board indices, and normalizing each depth sample. The result is a stable immutable analysis record."""
        best_move = self.best_move_index
        if best_move is not None:
            best_move = clampi(int(best_move), 0, BOARD_CELL_COUNT - 1)
        best_line: list[int] = []
        for value in tuple(self.best_line):
            try:
                index = int(value)
            except Exception:
                continue
            if 0 <= index < BOARD_CELL_COUNT:
                best_line.append(index)
        return OthelloAnalysis(side_to_move=normalize_side(self.side_to_move, default=SIDE_BLACK), best_move_index=best_move, best_line=tuple(best_line), score=float(self.score), solved=bool(self.solved), depth_reached=max(0, int(self.depth_reached)), depth_samples=tuple(sample.normalized() for sample in tuple(self.depth_samples)))


@dataclass(frozen=True)
class OthelloAnimationState:
    """I model one disc-flip trajectory as alpha = (square, from, to, elapsed, duration, delay, lift). The effective phase is t = clamp((elapsed - delay)/duration, 0, 1), and I preserve delay explicitly so that ripple schedules can be represented without duplicating per-mode timing code in the renderer."""
    square_index: int
    from_side: int
    to_side: int
    elapsed_s: float = 0.0
    duration_s: float = 0.22
    start_delay_s: float = 0.0
    lift_height: float = 0.075

    def normalized(self) -> "OthelloAnimationState":
        """I define N_alpha(alpha_raw) by clamping the square index into [0,63], enforcing elapsed >= 0, duration > 0, delay >= 0, and lift >= 0, and normalizing both side tokens. This prevents the renderer from receiving singular or negative timing parameters."""
        try:
            square_index = int(self.square_index)
        except Exception:
            square_index = 0
        square_index = clampi(square_index, 0, BOARD_CELL_COUNT - 1)
        elapsed = max(0.0, float(self.elapsed_s))
        duration = max(1e-6, float(self.duration_s))
        start_delay = max(0.0, float(self.start_delay_s))
        lift = max(0.0, float(self.lift_height))
        return OthelloAnimationState(square_index=int(square_index), from_side=normalize_side(self.from_side), to_side=normalize_side(self.to_side), elapsed_s=float(elapsed), duration_s=float(duration), start_delay_s=float(start_delay), lift_height=float(lift))

    def total_duration_s(self) -> float:
        """I define T(alpha) = delay + duration. I use this scalar as the completion threshold in the match controller so that staggered animations terminate only after the last delayed phase has elapsed."""
        normalized = self.normalized()
        return float(normalized.start_delay_s) + float(normalized.duration_s)

    def to_dict(self) -> dict[str, Any]:
        """I define phi_alpha : alpha -> JSONMap by serializing the normalized trajectory state, including its explicit start delay. I persist delay because ripple schedules are part of the semantic match state rather than transient renderer-local data."""
        normalized = self.normalized()
        return {"square_index": int(normalized.square_index), "from_side": str(side_name(normalized.from_side)), "to_side": str(side_name(normalized.to_side)), "elapsed_s": float(normalized.elapsed_s), "duration_s": float(normalized.duration_s), "start_delay_s": float(normalized.start_delay_s), "lift_height": float(normalized.lift_height)}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OthelloAnimationState":
        """I define weak deserialization for alpha by reading an arbitrary mapping and then applying N_alpha. This guarantees that restored animation state remains renderable even when persistence inputs are partial or stale."""
        if not isinstance(data, dict):
            return OthelloAnimationState(square_index=0, from_side=SIDE_EMPTY, to_side=SIDE_EMPTY)
        return OthelloAnimationState(square_index=int(data.get("square_index", 0)), from_side=normalize_side(data.get("from_side", SIDE_EMPTY)), to_side=normalize_side(data.get("to_side", SIDE_EMPTY)), elapsed_s=float(data.get("elapsed_s", 0.0)), duration_s=float(data.get("duration_s", 0.22)), start_delay_s=float(data.get("start_delay_s", 0.0)), lift_height=float(data.get("lift_height", 0.075))).normalized()


@dataclass(frozen=True)
class OthelloGameState:
    """I model the full persistent match state as G = (status, board, settings, player_side, ai_side, turn, t_b, t_w, move_count, passes, winner, message, last_move, animations, generation, legal_moves, thinking). I keep this record immutable so that controller transitions are explicit state-to-state transforms rather than hidden mutation sequences."""
    status: str = OTHELLO_GAME_STATE_IDLE
    board: tuple[int, ...] = field(default_factory=_default_initial_board)
    settings: OthelloSettings = field(default_factory=OthelloSettings)
    player_side: int = SIDE_BLACK
    ai_side: int = SIDE_WHITE
    current_turn: int = SIDE_BLACK
    black_time_remaining_s: float | None = DEFAULT_TIME_LIMIT_S
    white_time_remaining_s: float | None = DEFAULT_TIME_LIMIT_S
    move_count: int = 0
    consecutive_passes: int = 0
    winner: str | None = None
    message: str = "Right-click Start to begin a match. Use left click to place a disc."
    last_move_index: int | None = None
    animations: tuple[OthelloAnimationState, ...] = ()
    match_generation: int = 0
    legal_moves: tuple[int, ...] = ()
    thinking: bool = False

    def normalized(self) -> "OthelloGameState":
        """I define N_G(G_raw) by normalizing every scalar projection of the match state and by reconciling timer fields with the active timer mode. In particular, if tau(settings) = None then I force both clocks to None, and otherwise I clamp both clocks into [0, tau(settings)] so that timer invariants remain preserved under persistence and UI mutation."""
        status = normalize_game_status(self.status)
        settings = self.settings.normalized()
        player_side = normalize_player_side(self.player_side, default=settings.player_side)
        ai_side = other_side(player_side)
        current_turn = normalize_side(self.current_turn, default=SIDE_BLACK)
        if current_turn == SIDE_EMPTY:
            current_turn = SIDE_BLACK

        time_limit = settings.default_time_limit_s()
        if time_limit is None:
            black_time = None
            white_time = None
        else:
            base_black = time_limit if self.black_time_remaining_s is None else float(self.black_time_remaining_s)
            base_white = time_limit if self.white_time_remaining_s is None else float(self.white_time_remaining_s)
            black_time = float(clampf(base_black, 0.0, float(time_limit)))
            white_time = float(clampf(base_white, 0.0, float(time_limit)))

        try:
            move_count = max(0, int(self.move_count))
        except Exception:
            move_count = 0

        try:
            consecutive_passes = clampi(int(self.consecutive_passes), 0, 2)
        except Exception:
            consecutive_passes = 0

        try:
            generation = max(0, int(self.match_generation))
        except Exception:
            generation = 0

        last_move = self.last_move_index
        if last_move is not None:
            try:
                last_move = clampi(int(last_move), 0, BOARD_CELL_COUNT - 1)
            except Exception:
                last_move = None

        legal_moves: list[int] = []
        for value in tuple(self.legal_moves):
            try:
                index = int(value)
            except Exception:
                continue
            if 0 <= index < BOARD_CELL_COUNT and index not in legal_moves:
                legal_moves.append(index)

        animations = tuple(animation.normalized() for animation in tuple(self.animations))

        winner = None if self.winner is None else str(self.winner).strip().lower()
        if winner not in (None, "black", "white", OTHELLO_WINNER_DRAW):
            winner = None

        return OthelloGameState(status=str(status), board=coerce_board(self.board), settings=settings, player_side=int(player_side), ai_side=int(ai_side), current_turn=int(current_turn), black_time_remaining_s=black_time, white_time_remaining_s=white_time, move_count=int(move_count), consecutive_passes=int(consecutive_passes), winner=winner, message=str(self.message), last_move_index=last_move, animations=animations, match_generation=int(generation), legal_moves=tuple(legal_moves), thinking=bool(self.thinking))

    def to_dict(self) -> dict[str, Any]:
        """I define phi_G : G -> JSONMap over the normalized match state. I serialize board, settings, animation, and clock state explicitly so that a restarted application can reconstruct an algebraically equivalent match snapshot."""
        normalized = self.normalized()
        return {"status": str(normalized.status), "board": encode_board(normalized.board), "settings": normalized.settings.to_dict(), "player_side": str(side_name(normalized.player_side)), "ai_side": str(side_name(normalized.ai_side)), "current_turn": str(side_name(normalized.current_turn)), "black_time_remaining_s": None if normalized.black_time_remaining_s is None else float(normalized.black_time_remaining_s), "white_time_remaining_s": None if normalized.white_time_remaining_s is None else float(normalized.white_time_remaining_s), "move_count": int(normalized.move_count), "consecutive_passes": int(normalized.consecutive_passes), "winner": normalized.winner, "message": str(normalized.message), "last_move_index": normalized.last_move_index, "animations": [animation.to_dict() for animation in normalized.animations], "match_generation": int(normalized.match_generation), "legal_moves": [int(index) for index in normalized.legal_moves]}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OthelloGameState":
        """I define weak deserialization for G by reading an arbitrary mapping, coercing nested records independently, and finally applying N_G. This makes restored match state total even under legacy or partially corrupted payloads."""
        if not isinstance(data, dict):
            return OthelloGameState()

        settings = OthelloSettings.from_dict(data.get("settings",{}))

        animations_raw = data.get("animations",[])
        animations: list[OthelloAnimationState] = []
        if isinstance(animations_raw, list):
            for value in animations_raw:
                if isinstance(value, dict):
                    animations.append(OthelloAnimationState.from_dict(value))

        legal_moves_raw = data.get("legal_moves",[])
        legal_moves: list[int] = []
        if isinstance(legal_moves_raw, list):
            for value in legal_moves_raw:
                try:
                    index = int(value)
                except Exception:
                    continue
                if 0 <= index < BOARD_CELL_COUNT:
                    legal_moves.append(index)

        return OthelloGameState(status=normalize_game_status(data.get("status", OTHELLO_GAME_STATE_IDLE)), board=coerce_board(data.get("board", "")), settings=settings, player_side=normalize_player_side(data.get("player_side", settings.player_side)), ai_side=normalize_player_side(data.get("ai_side", other_side(settings.player_side)), default=SIDE_WHITE), current_turn=normalize_side(data.get("current_turn", SIDE_BLACK), default=SIDE_BLACK), black_time_remaining_s=data.get("black_time_remaining_s", settings.default_time_limit_s()), white_time_remaining_s=data.get("white_time_remaining_s", settings.default_time_limit_s()), move_count=int(data.get("move_count", 0)), consecutive_passes=int(data.get("consecutive_passes", 0)), winner=data.get("winner", None), message=str(data.get("message", "Right-click Start to begin a match. Use left click to place a disc.")), last_move_index=data.get("last_move_index", None), animations=tuple(animations), match_generation=int(data.get("match_generation", 0)), legal_moves=tuple(legal_moves)).normalized()


def empty_othello_game_state() -> OthelloGameState:
    """I define G_empty = N_G(OthelloGameState()). This constructor is the canonical zero-information state used when no persisted Othello match is available."""
    return OthelloGameState().normalized()
