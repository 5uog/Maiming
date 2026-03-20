# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer

from .....features.othello.domain.inventory.special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID
from .....features.othello.domain.game.board import OTHELLO_BOARD_SURFACE_Y, raycast_board_square, square_center
from .....features.othello.domain.game.rules import counts_for_board
from .....features.othello.domain.game.types import OTHELLO_GAME_STATE_AI_TURN, OTHELLO_GAME_STATE_FINISHED, OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_WINNER_DRAW, SIDE_BLACK, SIDE_WHITE
from .....application.services.audio import PLAYER_EVENT_OTHELLO_FLIP, PLAYER_EVENT_OTHELLO_PLACE
from .....features.othello.application.rendering.othello_render_state import OthelloRenderState
from . import settings_controller

if TYPE_CHECKING:
    from .....shared.core.math.vec3 import Vec3
    from ..gl_viewport_widget import GLViewportWidget

def bind_othello_controls(viewport: "GLViewportWidget") -> None:
    from . import interaction_controller

    viewport._othello_ai.move_ready.connect(lambda generation, move_index: on_ai_move_ready(viewport, int(generation), move_index))
    viewport._othello_settings.back_requested.connect(lambda: interaction_controller.back_from_othello_settings(viewport))
    viewport._othello_settings.settings_applied.connect(lambda settings: apply_settings(viewport, settings))

def _format_clock(seconds_remaining: float | None) -> str:
    if seconds_remaining is None:
        return "No limit"
    seconds = max(0, int(round(float(seconds_remaining))))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

def set_title_flash(viewport: "GLViewportWidget", text: str, *, duration_s: float) -> None:
    body = str(text).strip()
    if not body:
        return
    viewport._othello_title_flash_text = body
    viewport._othello_title_flash_until_s = time.perf_counter() + max(0.0, float(duration_s))

def clear_title_flash(viewport: "GLViewportWidget") -> None:
    viewport._othello_title_flash_text = ""
    viewport._othello_title_flash_until_s = 0.0

def track_message_for_title(viewport: "GLViewportWidget", message: str) -> None:
    body = str(message).strip()
    if body == viewport._last_othello_message:
        return
    viewport._last_othello_message = body
    lower = body.lower()
    if "must pass" in lower:
        set_title_flash(viewport, body, duration_s=1.75)
    elif "match started" in lower:
        set_title_flash(viewport, "Match started", duration_s=1.10)

def title_text(viewport: "GLViewportWidget", *, black_count: int, white_count: int) -> str:
    if not viewport._state.is_othello_space():
        return ""

    state = viewport._othello_match.game_state()
    if state.status == OTHELLO_GAME_STATE_FINISHED:
        if str(state.winner) == OTHELLO_WINNER_DRAW:
            return f"Draw\nBlack {int(black_count)}  White {int(white_count)}"
        winner_side = SIDE_BLACK if str(state.winner) == "black" else SIDE_WHITE
        winner = "Player" if int(winner_side) == int(state.player_side) else "AI"
        if "ran out of time" in str(state.message).lower():
            return f"{winner} wins on time\nBlack {int(black_count)}  White {int(white_count)}"
        return f"{winner} wins\nBlack {int(black_count)}  White {int(white_count)}"

    lines: list[str] = []
    now = time.perf_counter()
    if viewport._othello_title_flash_text and now < float(viewport._othello_title_flash_until_s):
        lines.append(str(viewport._othello_title_flash_text))
    if bool(state.thinking):
        lines.append("AI is thinking...")

    unique: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line and line not in seen:
            unique.append(line)
            seen.add(line)
    return "\n".join(unique)

def sync_hud_text(viewport: "GLViewportWidget") -> None:
    if not viewport._state.is_othello_space():
        viewport._othello_hud.set_text("")
        viewport._othello_hud.set_title_text("")
        viewport._last_othello_message = ""
        clear_title_flash(viewport)
        return

    state = viewport._othello_match.game_state()
    track_message_for_title(viewport, state.message)
    black_count, white_count = counts_for_board(state.board)

    if state.status == OTHELLO_GAME_STATE_PLAYER_TURN:
        turn_text = "Your turn"
    elif state.status == OTHELLO_GAME_STATE_AI_TURN:
        turn_text = "AI turn"
    else:
        turn_text = state.status.replace("_", " ").title()

    player_color = "Black" if int(state.player_side) == int(SIDE_BLACK) else "White"
    ai_color = "White" if int(state.ai_side) == int(SIDE_WHITE) else "Black"
    difficulty = str(state.settings.difficulty).title()

    viewport._othello_hud.set_text("\n".join([str(turn_text), f"Black {int(black_count)}  White {int(white_count)}", f"AI {difficulty}  You {player_color}  AI {ai_color}", f"Black clock: {_format_clock(state.black_time_remaining_s)}", f"White clock: {_format_clock(state.white_time_remaining_s)}", str(state.message)]))
    viewport._othello_hud.set_title_text(title_text(viewport, black_count=int(black_count), white_count=int(white_count)))

def build_render_state(viewport: "GLViewportWidget") -> OthelloRenderState | None:
    if not viewport._state.is_othello_space():
        return None

    game_state = viewport._othello_match.game_state()
    legal_moves = game_state.legal_moves if game_state.status == OTHELLO_GAME_STATE_PLAYER_TURN else ()

    return OthelloRenderState(enabled=True, board=tuple(game_state.board), legal_move_indices=tuple(int(index) for index in tuple(legal_moves)), hover_square_index=viewport._othello_hover_square, last_move_index=game_state.last_move_index, animations=tuple(game_state.animations))

def refresh_hover_square(viewport: "GLViewportWidget", snapshot) -> None:
    viewport._othello_hover_square = None
    if not viewport._state.is_othello_space() or viewport._overlays.any_modal_open():
        return

    game_state = viewport._othello_match.game_state()
    if game_state.status != OTHELLO_GAME_STATE_PLAYER_TURN:
        return

    render_eye, _yaw, _pitch, _roll, render_direction = viewport._effective_camera_from_snapshot(snapshot)
    square_index = raycast_board_square(render_eye, render_direction)
    if square_index is None or int(square_index) not in set(game_state.legal_moves):
        return
    viewport._othello_hover_square = int(square_index)

def sync_settings_values(viewport: "GLViewportWidget") -> None:
    viewport._othello_settings.sync_values(viewport._state.othello_settings)

def _play_move_audio(viewport: "GLViewportWidget", state) -> None:
    if state.last_move_index is not None:
        place_x, place_z = square_center(int(state.last_move_index))
        viewport._audio.play_othello_event(event_name=PLAYER_EVENT_OTHELLO_PLACE, position=(float(place_x), float(OTHELLO_BOARD_SURFACE_Y) + 0.15, float(place_z)))
    for animation in tuple(state.animations):
        flip_x, flip_z = square_center(int(animation.square_index))
        viewport._audio.play_othello_event(event_name=PLAYER_EVENT_OTHELLO_FLIP, position=(float(flip_x), float(OTHELLO_BOARD_SURFACE_Y) + 0.15, float(flip_z)))

def apply_settings(viewport: "GLViewportWidget", settings) -> None:
    viewport._state.othello_settings = settings.normalized()
    viewport._state.normalize()
    viewport._othello_match.set_default_settings(viewport._state.othello_settings)
    sync_hud_text(viewport)
    viewport.save_state()

def clear_state_for_space_switch(viewport: "GLViewportWidget") -> None:
    viewport._othello_match.settle_animations()
    viewport._pending_othello_ai_result = None
    viewport._othello_ai_request_armed = False
    viewport._othello_hover_square = None
    clear_title_flash(viewport)
    viewport._last_othello_message = ""

def maybe_request_ai(viewport: "GLViewportWidget") -> None:
    if not viewport._state.is_othello_space():
        return
    if (viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead()):
        return

    state = viewport._othello_match.game_state()
    if (state.status != OTHELLO_GAME_STATE_AI_TURN or bool(state.thinking) or bool(viewport._othello_ai_request_armed)):
        return

    viewport._othello_match.set_ai_thinking(True)
    state = viewport._othello_match.game_state()
    sync_hud_text(viewport)

    generation = int(state.match_generation)
    board = tuple(state.board)
    side = int(state.ai_side)
    difficulty = str(state.settings.difficulty)
    seed = int(state.match_generation * 257 + state.move_count * 17 + 3)

    viewport._othello_ai_request_armed = True
    QTimer.singleShot(0, lambda generation=generation, board=board, side=side, difficulty=difficulty, seed=seed: dispatch_ai_request(viewport, generation=generation, board=board, side=side, difficulty=difficulty, seed=seed))

def dispatch_ai_request(viewport: "GLViewportWidget", *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int) -> None:
    viewport._othello_ai_request_armed = False
    if not viewport._state.is_othello_space():
        return
    if (viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead()):
        return

    state = viewport._othello_match.game_state()
    if (int(state.match_generation) != int(generation) or state.status != OTHELLO_GAME_STATE_AI_TURN or not bool(state.thinking)):
        return

    viewport._othello_ai.request_move(generation=int(generation), board=tuple(board), side=int(side), difficulty=str(difficulty), seed=int(seed))

def consume_pending_ai_result(viewport: "GLViewportWidget") -> None:
    if viewport._pending_othello_ai_result is None:
        return
    if (viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead()):
        return

    generation, move_index = viewport._pending_othello_ai_result
    viewport._pending_othello_ai_result = None
    apply_ai_result(viewport, int(generation), move_index)

def apply_ai_result(viewport: "GLViewportWidget", generation: int, move_index: int | None) -> None:
    state = viewport._othello_match.game_state()
    if int(generation) != int(state.match_generation) or state.status != OTHELLO_GAME_STATE_AI_TURN:
        return

    viewport._othello_ai_request_armed = False
    if viewport._othello_match.submit_ai_move(move_index):
        _play_move_audio(viewport, viewport._othello_match.game_state())
    sync_hud_text(viewport)

def on_ai_move_ready(viewport: "GLViewportWidget", generation: int, move_index: object) -> None:
    result = None if move_index is None else int(move_index)
    if (viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead()):
        viewport._pending_othello_ai_result = (int(generation), result)
        return
    apply_ai_result(viewport, int(generation), result)

def handle_left_click(viewport: "GLViewportWidget", render_eye: "Vec3", render_direction: "Vec3") -> None:
    viewport._first_person_motion.trigger_left_swing()
    square_index = raycast_board_square(render_eye, render_direction)
    if square_index is not None and viewport._othello_match.submit_player_move(int(square_index)):
        _play_move_audio(viewport, viewport._othello_match.game_state())
        sync_hud_text(viewport)
        maybe_request_ai(viewport)

def handle_right_click(viewport: "GLViewportWidget") -> None:
    from . import interaction_controller

    item_id = settings_controller.current_item_id(viewport)
    if item_id == OTHELLO_START_ITEM_ID:
        viewport._othello_match.restart_match()
        viewport._pending_othello_ai_result = None
        viewport._othello_ai_request_armed = False
        viewport._first_person_motion.trigger_right_swing(success=True)
        sync_hud_text(viewport)
        maybe_request_ai(viewport)
        return

    if item_id == OTHELLO_SETTINGS_ITEM_ID:
        viewport._first_person_motion.trigger_right_swing(success=True)
        interaction_controller.open_othello_settings_from_item(viewport)