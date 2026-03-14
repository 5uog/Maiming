# FILE: src/maiming/domain/othello/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

SIDE_EMPTY: int = 0
SIDE_BLACK: int = 1
SIDE_WHITE: int = 2

_SIDE_TOKENS: dict[int, str] = {SIDE_EMPTY: ".", SIDE_BLACK: "B", SIDE_WHITE: "W"}
_TOKEN_SIDES: dict[str, int] = {value: key for key, value in _SIDE_TOKENS.items()}

OTHELLO_DIFFICULTY_WEAK: str = "weak"
OTHELLO_DIFFICULTY_MEDIUM: str = "medium"
OTHELLO_DIFFICULTY_STRONG: str = "strong"
OTHELLO_DIFFICULTIES: tuple[str, ...] = (OTHELLO_DIFFICULTY_WEAK, OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_STRONG)

OTHELLO_TIME_CONTROL_PER_SIDE_20M: str = "per_side_20m"
OTHELLO_TIME_CONTROL_NONE: str = "none"
OTHELLO_TIME_CONTROLS: tuple[str, ...] = (OTHELLO_TIME_CONTROL_PER_SIDE_20M, OTHELLO_TIME_CONTROL_NONE)

OTHELLO_GAME_STATE_IDLE: str = "idle"
OTHELLO_GAME_STATE_PLAYER_TURN: str = "player_turn"
OTHELLO_GAME_STATE_AI_TURN: str = "ai_turn"
OTHELLO_GAME_STATE_ANIMATING: str = "animating"
OTHELLO_GAME_STATE_FINISHED: str = "finished"
OTHELLO_GAME_STATUSES: tuple[str, ...] = (OTHELLO_GAME_STATE_IDLE, OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_GAME_STATE_AI_TURN, OTHELLO_GAME_STATE_ANIMATING, OTHELLO_GAME_STATE_FINISHED)

OTHELLO_WINNER_DRAW: str = "draw"

DEFAULT_TIME_LIMIT_S: float = 20.0 * 60.0
BOARD_CELL_COUNT: int = 64

def normalize_side(value: object, *, default: int = SIDE_EMPTY) -> int:
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
    norm = normalize_side(side, default=SIDE_EMPTY)
    if norm == SIDE_BLACK:
        return SIDE_WHITE
    if norm == SIDE_WHITE:
        return SIDE_BLACK
    return SIDE_EMPTY

def normalize_player_side(value: object, *, default: int = SIDE_BLACK) -> int:
    side = normalize_side(value, default=default)
    if side == SIDE_EMPTY:
        return SIDE_BLACK if int(default) == SIDE_EMPTY else normalize_side(default, default=SIDE_BLACK)
    return side

def normalize_difficulty(value: object, *, default: str = OTHELLO_DIFFICULTY_MEDIUM) -> str:
    raw = str(value).strip().lower()
    if raw in OTHELLO_DIFFICULTIES:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_DIFFICULTIES:
        return fallback
    return OTHELLO_DIFFICULTY_MEDIUM

def normalize_time_control(value: object, *, default: str = OTHELLO_TIME_CONTROL_PER_SIDE_20M) -> str:
    raw = str(value).strip().lower()
    if raw in ("no_limit", "unlimited"):
        raw = OTHELLO_TIME_CONTROL_NONE
    if raw in OTHELLO_TIME_CONTROLS:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_TIME_CONTROLS:
        return fallback
    return OTHELLO_TIME_CONTROL_PER_SIDE_20M

def normalize_game_status(value: object, *, default: str = OTHELLO_GAME_STATE_IDLE) -> str:
    raw = str(value).strip().lower()
    if raw in OTHELLO_GAME_STATUSES:
        return raw
    fallback = str(default).strip().lower()
    if fallback in OTHELLO_GAME_STATUSES:
        return fallback
    return OTHELLO_GAME_STATE_IDLE

def side_name(side: int) -> str:
    norm = normalize_side(side, default=SIDE_EMPTY)
    if norm == SIDE_BLACK:
        return "black"
    if norm == SIDE_WHITE:
        return "white"
    return "empty"

def encode_board(board: tuple[int, ...] | list[int]) -> str:
    cells: list[str] = []
    seq = tuple(board)
    for index in range(BOARD_CELL_COUNT):
        side = normalize_side(seq[index] if index < len(seq) else SIDE_EMPTY)
        cells.append(_SIDE_TOKENS[side])
    return "".join(cells)

def decode_board(raw: object) -> tuple[int, ...]:
    text = str(raw or "")
    cells: list[int] = []
    for token in text[:BOARD_CELL_COUNT]:
        cells.append(int(_TOKEN_SIDES.get(str(token).upper(), SIDE_EMPTY)))
    while len(cells) < BOARD_CELL_COUNT:
        cells.append(SIDE_EMPTY)
    return tuple(cells[:BOARD_CELL_COUNT])

@dataclass(frozen=True)
class OthelloSettings:
    difficulty: str = OTHELLO_DIFFICULTY_MEDIUM
    time_control: str = OTHELLO_TIME_CONTROL_PER_SIDE_20M
    player_side: int = SIDE_BLACK

    def normalized(self) -> "OthelloSettings":
        return OthelloSettings(difficulty=normalize_difficulty(self.difficulty), time_control=normalize_time_control(self.time_control), player_side=normalize_player_side(self.player_side))

    def default_time_limit_s(self) -> float | None:
        if normalize_time_control(self.time_control) == OTHELLO_TIME_CONTROL_NONE:
            return None
        return float(DEFAULT_TIME_LIMIT_S)

    def to_dict(self) -> dict[str, Any]:
        normalized = self.normalized()
        return {"difficulty": str(normalized.difficulty), "time_control": str(normalized.time_control), "player_side": str(side_name(normalized.player_side))}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OthelloSettings":
        if not isinstance(data, dict):
            return OthelloSettings()
        return OthelloSettings(difficulty=normalize_difficulty(data.get("difficulty", OTHELLO_DIFFICULTY_MEDIUM)), time_control=normalize_time_control(data.get("time_control", OTHELLO_TIME_CONTROL_PER_SIDE_20M)), player_side=normalize_player_side(data.get("player_side", SIDE_BLACK)))

@dataclass(frozen=True)
class OthelloAnimationState:
    square_index: int
    from_side: int
    to_side: int
    elapsed_s: float = 0.0
    duration_s: float = 0.22
    lift_height: float = 0.075

    def normalized(self) -> "OthelloAnimationState":
        try:
            square_index = int(self.square_index)
        except Exception:
            square_index = 0
        square_index = max(0, min(BOARD_CELL_COUNT - 1, square_index))

        elapsed = max(0.0, float(self.elapsed_s))
        duration = max(1e-6, float(self.duration_s))
        lift = max(0.0, float(self.lift_height))

        return OthelloAnimationState(square_index=int(square_index), from_side=normalize_side(self.from_side), to_side=normalize_side(self.to_side), elapsed_s=float(elapsed), duration_s=float(duration), lift_height=float(lift))

    def to_dict(self) -> dict[str, Any]:
        normalized = self.normalized()
        return {"square_index": int(normalized.square_index), "from_side": str(side_name(normalized.from_side)), "to_side": str(side_name(normalized.to_side)), "elapsed_s": float(normalized.elapsed_s), "duration_s": float(normalized.duration_s), "lift_height": float(normalized.lift_height)}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OthelloAnimationState":
        if not isinstance(data, dict):
            return OthelloAnimationState(square_index=0, from_side=SIDE_EMPTY, to_side=SIDE_EMPTY)
        return OthelloAnimationState(square_index=int(data.get("square_index", 0)), from_side=normalize_side(data.get("from_side", SIDE_EMPTY)), to_side=normalize_side(data.get("to_side", SIDE_EMPTY)), elapsed_s=float(data.get("elapsed_s", 0.0)), duration_s=float(data.get("duration_s", 0.22)), lift_height=float(data.get("lift_height", 0.075))).normalized()

@dataclass(frozen=True)
class OthelloGameState:
    status: str = OTHELLO_GAME_STATE_IDLE
    board: tuple[int, ...] = field(default_factory=lambda: decode_board(""))
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
        status = normalize_game_status(self.status)
        settings = self.settings.normalized()
        player_side = normalize_player_side(self.player_side, default=settings.player_side)
        ai_side = other_side(player_side)
        current_turn = normalize_side(self.current_turn, default=SIDE_BLACK)
        if current_turn == SIDE_EMPTY:
            current_turn = SIDE_BLACK

        if settings.time_control == OTHELLO_TIME_CONTROL_NONE:
            black_time = None
            white_time = None
        else:
            base_black = self.black_time_remaining_s if self.black_time_remaining_s is not None else DEFAULT_TIME_LIMIT_S
            base_white = self.white_time_remaining_s if self.white_time_remaining_s is not None else DEFAULT_TIME_LIMIT_S
            black_time = float(max(0.0, float(base_black)))
            white_time = float(max(0.0, float(base_white)))

        try:
            move_count = max(0, int(self.move_count))
        except Exception:
            move_count = 0

        try:
            consecutive_passes = max(0, min(2, int(self.consecutive_passes)))
        except Exception:
            consecutive_passes = 0

        try:
            generation = max(0, int(self.match_generation))
        except Exception:
            generation = 0

        last_move = self.last_move_index
        if last_move is not None:
            try:
                last_move = max(0, min(BOARD_CELL_COUNT - 1, int(last_move)))
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

        return OthelloGameState(status=str(status), board=decode_board(encode_board(self.board)), settings=settings, player_side=int(player_side), ai_side=int(ai_side), current_turn=int(current_turn), black_time_remaining_s=black_time, white_time_remaining_s=white_time, move_count=int(move_count), consecutive_passes=int(consecutive_passes), winner=winner, message=str(self.message), last_move_index=last_move, animations=animations, match_generation=int(generation), legal_moves=tuple(legal_moves), thinking=bool(self.thinking))

    def to_dict(self) -> dict[str, Any]:
        normalized = self.normalized()
        return {"status": str(normalized.status), "board": encode_board(normalized.board), "settings": normalized.settings.to_dict(), "player_side": str(side_name(normalized.player_side)), "ai_side": str(side_name(normalized.ai_side)), "current_turn": str(side_name(normalized.current_turn)), "black_time_remaining_s": None if normalized.black_time_remaining_s is None else float(normalized.black_time_remaining_s), "white_time_remaining_s": None if normalized.white_time_remaining_s is None else float(normalized.white_time_remaining_s), "move_count": int(normalized.move_count), "consecutive_passes": int(normalized.consecutive_passes), "winner": normalized.winner, "message": str(normalized.message), "last_move_index": normalized.last_move_index, "animations": [animation.to_dict() for animation in normalized.animations], "match_generation": int(normalized.match_generation), "legal_moves": [int(index) for index in normalized.legal_moves]}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OthelloGameState":
        if not isinstance(data, dict):
            return OthelloGameState()

        settings = OthelloSettings.from_dict(data.get("settings", {}))

        animations_raw = data.get("animations", [])
        animations: list[OthelloAnimationState] = []
        if isinstance(animations_raw, list):
            for value in animations_raw:
                if isinstance(value, dict):
                    animations.append(OthelloAnimationState.from_dict(value))

        legal_moves_raw = data.get("legal_moves", [])
        legal_moves: list[int] = []
        if isinstance(legal_moves_raw, list):
            for value in legal_moves_raw:
                try:
                    index = int(value)
                except Exception:
                    continue
                if 0 <= index < BOARD_CELL_COUNT:
                    legal_moves.append(index)

        return OthelloGameState(status=normalize_game_status(data.get("status", OTHELLO_GAME_STATE_IDLE)), board=decode_board(data.get("board", "")), settings=settings, player_side=normalize_player_side(data.get("player_side", settings.player_side)), ai_side=normalize_player_side(data.get("ai_side", other_side(settings.player_side)), default=SIDE_WHITE), current_turn=normalize_side(data.get("current_turn", SIDE_BLACK), default=SIDE_BLACK), black_time_remaining_s=data.get("black_time_remaining_s", settings.default_time_limit_s()), white_time_remaining_s=data.get("white_time_remaining_s", settings.default_time_limit_s()), move_count=int(data.get("move_count", 0)), consecutive_passes=int(data.get("consecutive_passes", 0)), winner=data.get("winner", None), message=str(data.get("message", "Right-click Start to begin a match. Use left click to place a disc.")), last_move_index=data.get("last_move_index", None), animations=tuple(animations), match_generation=int(data.get("match_generation", 0)), legal_moves=tuple(legal_moves)).normalized()

def empty_othello_game_state() -> OthelloGameState:
    return OthelloGameState().normalized()