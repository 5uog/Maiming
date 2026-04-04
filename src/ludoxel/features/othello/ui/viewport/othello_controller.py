# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ludoxel.application.audio import PLAYER_EVENT_OTHELLO_FLIP, PLAYER_EVENT_OTHELLO_PLACE
from ludoxel.features.othello.rendering.othello_render_state import OthelloRenderState
from ludoxel.features.othello.domain.game.board import OTHELLO_BOARD_SURFACE_Y, raycast_board_square, square_center, square_index_to_name
from ludoxel.features.othello.domain.book.opening_book import export_opening_book_file, import_opening_book_file, opening_book_summary
from ludoxel.features.othello.domain.game.rules import counts_for_board
from ludoxel.features.othello.domain.game.types import OTHELLO_GAME_STATE_AI_TURN, OTHELLO_GAME_STATE_FINISHED, OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_WINNER_DRAW, OthelloAnalysis, SIDE_BLACK, SIDE_WHITE, difficulty_display_name
from ludoxel.features.othello.domain.inventory.special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID
import ludoxel.shared.ui.viewport.controllers.settings_controller as settings_controller

if TYPE_CHECKING:
    from ludoxel.shared.math.vec3 import Vec3
    from ludoxel.shared.ui.viewport.gl_viewport_widget import GLViewportWidget


def bind_othello_controls(viewport: "GLViewportWidget") -> None:
    import ludoxel.shared.ui.viewport.controllers.interaction_controller as interaction_controller

    viewport._othello_ai.move_ready.connect(lambda generation, move_index: on_ai_move_ready(viewport, int(generation), move_index))
    viewport._othello_ai.analysis_ready.connect(lambda generation, analysis: on_analysis_ready(viewport, int(generation), analysis))
    viewport._othello_ai.book_learning_progress.connect(lambda payload: on_book_learning_progress(viewport, payload))
    viewport._othello_ai.book_learning_ready.connect(lambda payload: on_book_learning_ready(viewport, payload))
    viewport._othello_settings.back_requested.connect(lambda: interaction_controller.back_from_othello_settings(viewport))
    viewport._othello_settings.settings_applied.connect(lambda settings: apply_settings(viewport, settings))
    viewport._othello_settings.book_learning_requested.connect(lambda settings: request_book_learning(viewport, settings))
    viewport._othello_settings.book_learning_cancel_requested.connect(lambda: cancel_book_learning(viewport))
    viewport._othello_settings.book_import_requested.connect(lambda: import_book(viewport))
    viewport._othello_settings.book_export_requested.connect(lambda: export_book(viewport))


def _ensure_book_summary_loaded(viewport: "GLViewportWidget") -> None:
    if str(viewport._othello_book_summary_text).strip():
        return
    _refresh_book_summary(viewport)


def _format_clock(seconds_remaining: float | None) -> str:
    if seconds_remaining is None:
        return "No limit"
    seconds = max(0, int(round(float(seconds_remaining))))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _format_best_line(best_line: tuple[int, ...], *, limit: int = 8) -> str:
    if not best_line:
        return "-"
    shown = [square_index_to_name(int(move_index)) for move_index in tuple(best_line)[:max(1, int(limit))]]
    hidden = max(0, len(tuple(best_line)) - len(shown))
    if int(hidden) > 0:
        shown.append(f"(+{int(hidden)})")
    return " ".join(shown)


def _format_best_move(best_move_index: int | None) -> str:
    if best_move_index is None:
        return "-"
    return square_index_to_name(int(best_move_index))


def _analysis_player_edge(viewport: "GLViewportWidget") -> float | None:
    analysis = viewport._othello_analysis.normalized()
    state = viewport._othello_match.game_state()
    if int(analysis.depth_reached) <= 0 and analysis.best_move_index is None:
        return None
    perspective_score = float(analysis.score)
    if int(analysis.side_to_move) != int(state.player_side):
        perspective_score = -float(perspective_score)
    return float(perspective_score)


def _analysis_graph_samples(viewport: "GLViewportWidget") -> tuple[tuple[int, float, bool], ...]:
    analysis = viewport._othello_analysis.normalized()
    state = viewport._othello_match.game_state()
    if not analysis.depth_samples:
        return ()
    sign = 1.0 if int(analysis.side_to_move) == int(state.player_side) else -1.0
    return tuple((int(sample.depth), float(sample.score) * float(sign), bool(sample.solved)) for sample in tuple(analysis.depth_samples)[-12:])


def _book_learning_progress(viewport: "GLViewportWidget") -> dict[str, object] | None:
    progress = viewport._othello_book_learning_progress
    return progress if isinstance(progress, dict) else None


def _refresh_book_summary(viewport: "GLViewportWidget") -> None:
    summary = opening_book_summary(viewport._project_root)
    viewport._othello_book_summary_text = f"Bundled {int(summary.bundled_lines)} lines | User {int(summary.user_lines)} lines | Total {int(summary.total_lines)} lines"
    viewport._othello_settings.set_book_summary_text(viewport._othello_book_summary_text)


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


def _banner_text(viewport: "GLViewportWidget", *, black_count: int, white_count: int) -> str:
    if not viewport._state.is_othello_space():
        return ""

    if bool(viewport._othello_book_learning_running):
        return str(viewport._othello_book_learning_status_text or "Learning opening book...")

    state = viewport._othello_match.game_state()
    if state.status == OTHELLO_GAME_STATE_FINISHED:
        if str(state.winner) == OTHELLO_WINNER_DRAW:
            return f"Draw | Black {int(black_count)} White {int(white_count)}"
        winner_side = SIDE_BLACK if str(state.winner) == "black" else SIDE_WHITE
        winner = "Player" if int(winner_side) == int(state.player_side) else "AI"
        if "ran out of time" in str(state.message).lower():
            return f"{winner} wins on time | Black {int(black_count)} White {int(white_count)}"
        return f"{winner} wins | Black {int(black_count)} White {int(white_count)}"

    now = time.perf_counter()
    if viewport._othello_title_flash_text and now < float(viewport._othello_title_flash_until_s):
        return str(viewport._othello_title_flash_text)
    if bool(state.thinking):
        return "AI is thinking..."
    return ""


def sync_hud_text(viewport: "GLViewportWidget") -> None:
    if not viewport._state.is_othello_space():
        viewport._othello_hud_signature = None
        viewport._othello_hud.set_texts(left_text="", right_text="", title_text="", graph_samples=(), graph_current_edge=None)
        viewport._last_othello_message = ""
        clear_title_flash(viewport)
        viewport._othello_analysis = OthelloAnalysis().normalized()
        return

    _ensure_book_summary_loaded(viewport)

    state = viewport._othello_match.game_state()
    analysis = viewport._othello_analysis.normalized()
    learning_progress = _book_learning_progress(viewport)
    track_message_for_title(viewport, state.message)
    board_for_display = tuple(state.board)
    if learning_progress is not None:
        board_for_display = tuple(learning_progress.get("board", board_for_display))
    black_count, white_count = counts_for_board(board_for_display)

    if bool(viewport._othello_book_learning_running):
        turn_text = "Book learning"
    elif state.status == OTHELLO_GAME_STATE_PLAYER_TURN:
        turn_text = "Your turn"
    elif state.status == OTHELLO_GAME_STATE_AI_TURN:
        turn_text = "AI turn"
    else:
        turn_text = state.status.replace("_", " ").title()

    player_color = "Black" if int(state.player_side) == int(SIDE_BLACK) else "White"
    ai_color = "White" if int(state.ai_side) == int(SIDE_WHITE) else "Black"
    difficulty = difficulty_display_name(state.settings.difficulty)
    black_clock = _format_clock(state.black_time_remaining_s)
    white_clock = _format_clock(state.white_time_remaining_s)
    banner = _banner_text(viewport, black_count=int(black_count), white_count=int(white_count))
    hover_square = viewport._othello_hover_square
    hover_text = "-"
    if hover_square is not None:
        hover_text = square_index_to_name(int(hover_square))
        if int(hover_square) in set(state.legal_moves):
            hover_text += " legal"
    if learning_progress is not None:
        line = tuple(int(move) for move in tuple(learning_progress.get("line",())))
        learning_line_text = _format_best_line(line, limit=6)
        learning_side = learning_progress.get("side_to_move", None)
        learning_side_text = "Black" if int(learning_side or SIDE_BLACK) == int(SIDE_BLACK) else "White"
        explored_positions = int(learning_progress.get("explored_positions", 0))
        remaining_depth = int(learning_progress.get("remaining_depth", 0))
    else:
        learning_line_text = "-"
        learning_side_text = "-"
        explored_positions = 0
        remaining_depth = 0
    player_edge = _analysis_player_edge(viewport)
    graph_samples = _analysis_graph_samples(viewport)
    best_move_text = _format_best_move(analysis.best_move_index)
    best_line_text = _format_best_line(tuple(analysis.best_line), limit=6)

    left_lines: list[str] = []
    left_lines.append(f"Turn: {turn_text}")
    left_lines.append(f"Black {int(black_count)}  White {int(white_count)}")
    left_lines.append(f"Hover: {hover_text}")
    left_lines.append(f"Best move: {best_move_text}")
    left_lines.append(f"Best line: {best_line_text}")
    if learning_progress is not None:
        left_lines.append(f"Learning line: {learning_line_text}")
        left_lines.append(f"Learning side: {learning_side_text} | Explored {explored_positions} | Depth {remaining_depth}")
    if player_edge is None:
        left_lines.append("Advantage: unavailable")
    else:
        left_lines.append(f"Player edge {float(player_edge):+7.1f} | AI edge {-float(player_edge):+7.1f}")
    left_lines.append(f"Search depth {int(analysis.depth_reached)} | Solved {int(bool(analysis.solved))}")
    left_lines.append(str(state.message))

    right_lines = [f"AI {difficulty} | You {player_color} | AI {ai_color}", f"Black clock: {black_clock}", f"White clock: {white_clock}", f"Sacrifice {int(state.settings.sacrifice_level)} | Threads {int(state.settings.thread_count)} | Hash {int(state.settings.hash_level)}", str(viewport._othello_book_summary_text)]

    signature = (tuple(left_lines), tuple(right_lines), str(banner), tuple(graph_samples), (None if player_edge is None else round(float(player_edge), 4)))
    if viewport._othello_hud_signature == signature:
        return
    viewport._othello_hud_signature = signature
    viewport._othello_hud.set_texts(left_text="\n".join(left_lines), right_text="\n".join(right_lines), title_text=str(banner), graph_samples=tuple(graph_samples), graph_current_edge=player_edge)


def build_render_state(viewport: "GLViewportWidget") -> OthelloRenderState | None:
    if not viewport._state.is_othello_space():
        viewport._othello_render_state_cache_key = None
        viewport._othello_render_state_cache = None
        return None

    game_state = viewport._othello_match.game_state()
    learning_progress = _book_learning_progress(viewport)
    if learning_progress is not None:
        learning_board = tuple(learning_progress.get("board", game_state.board))
        learning_legal_moves = tuple(int(move) for move in tuple(learning_progress.get("legal_moves",())))
        learning_line = tuple(int(move) for move in tuple(learning_progress.get("line",())))
        learning_last_move = None if not learning_line else int(learning_line[-1])
        cache_key = ("learning", learning_board, learning_legal_moves, learning_last_move)
        if viewport._othello_render_state_cache_key == cache_key and viewport._othello_render_state_cache is not None:
            return viewport._othello_render_state_cache
        render_state = OthelloRenderState(enabled=True, board=tuple(learning_board), legal_move_indices=tuple(learning_legal_moves), hover_square_index=None, last_move_index=learning_last_move, animations=())
        viewport._othello_render_state_cache_key = cache_key
        viewport._othello_render_state_cache = render_state
        return render_state

    cache_key = (int(id(game_state)), viewport._othello_hover_square)
    if viewport._othello_render_state_cache_key == cache_key and viewport._othello_render_state_cache is not None:
        return viewport._othello_render_state_cache
    legal_moves = game_state.legal_moves if game_state.status == OTHELLO_GAME_STATE_PLAYER_TURN else ()
    render_state = OthelloRenderState(enabled=True, board=game_state.board, legal_move_indices=legal_moves, hover_square_index=viewport._othello_hover_square, last_move_index=game_state.last_move_index, animations=game_state.animations)
    viewport._othello_render_state_cache_key = cache_key
    viewport._othello_render_state_cache = render_state
    return render_state


def refresh_hover_square(viewport: "GLViewportWidget", snapshot) -> None:
    viewport._othello_hover_square = None
    if not viewport._state.is_othello_space() or viewport._overlays.any_modal_open():
        return

    interaction_eye, _yaw, _pitch, interaction_direction = viewport._interaction_pose_from_snapshot(snapshot)
    square_index = raycast_board_square(interaction_eye, interaction_direction)
    if square_index is None:
        return
    viewport._othello_hover_square = int(square_index)


def sync_settings_values(viewport: "GLViewportWidget") -> None:
    if viewport._state.is_othello_space() or viewport._overlays.othello_settings_open():
        _ensure_book_summary_loaded(viewport)
    viewport._othello_settings.sync_values(viewport._state.othello_settings)
    viewport._othello_settings.set_book_summary_text(str(viewport._othello_book_summary_text))
    viewport._othello_settings.set_learning_running(bool(viewport._othello_book_learning_running), status_text=str(viewport._othello_book_learning_status_text))


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
    viewport._othello_analysis_request_signature = None
    if not viewport._overlays.othello_settings_open():
        maybe_request_analysis(viewport)


def request_book_learning(viewport: "GLViewportWidget", settings) -> None:
    normalized = settings.normalized()
    viewport._othello_match.reset_to_idle()
    viewport._pending_othello_ai_result = None
    viewport._othello_ai_request_armed = False
    viewport._othello_hover_square = None
    viewport._othello_analysis = OthelloAnalysis().normalized()
    viewport._othello_analysis_request_signature = None
    viewport._othello_book_learning_running = True
    viewport._othello_book_learning_status_text = "Book learning started."
    viewport._othello_book_learning_progress = None
    viewport._othello_settings.set_learning_running(True, status_text=str(viewport._othello_book_learning_status_text))
    sync_hud_text(viewport)
    viewport.update()
    viewport._othello_ai.request_book_learning(settings=normalized, project_root=str(viewport._project_root))


def cancel_book_learning(viewport: "GLViewportWidget") -> None:
    if not bool(viewport._othello_book_learning_running):
        return
    viewport._othello_book_learning_status_text = "Cancelling opening book learning..."
    viewport._othello_settings.set_learning_running(True, status_text=str(viewport._othello_book_learning_status_text))
    sync_hud_text(viewport)
    viewport.update()
    viewport._othello_ai.cancel_book_learning()


def import_book(viewport: "GLViewportWidget") -> None:
    selected_path, _selected_filter = QFileDialog.getOpenFileName(viewport._othello_settings, "Import Opening Book", str(viewport._project_root), "JSON Files (*.json)")
    if not str(selected_path).strip():
        return
    try:
        summary = import_opening_book_file(selected_path, project_root=viewport._project_root)
    except Exception as exc:
        QMessageBox.warning(viewport._othello_settings, "Import Opening Book", str(exc))
        return
    viewport._othello_book_learning_status_text = f"Opening book imported. Bundled {int(summary.bundled_lines)} | User {int(summary.user_lines)} | Total {int(summary.total_lines)}."
    _refresh_book_summary(viewport)
    viewport._othello_analysis_request_signature = None
    viewport._othello_settings.set_learning_running(False, status_text=str(viewport._othello_book_learning_status_text))
    sync_hud_text(viewport)
    maybe_request_analysis(viewport)
    viewport.update()


def export_book(viewport: "GLViewportWidget") -> None:
    selected_path, _selected_filter = QFileDialog.getSaveFileName(viewport._othello_settings, "Export Opening Book", str(viewport._project_root / "configs" / "othello_opening_book_export.json"), "JSON Files (*.json)")
    if not str(selected_path).strip():
        return
    try:
        export_path = export_opening_book_file(selected_path, project_root=viewport._project_root)
    except Exception as exc:
        QMessageBox.warning(viewport._othello_settings, "Export Opening Book", str(exc))
        return
    viewport._othello_book_learning_status_text = f"Opening book exported to {export_path.name}."
    viewport._othello_settings.set_learning_running(False, status_text=str(viewport._othello_book_learning_status_text))
    sync_hud_text(viewport)
    viewport.update()


def on_book_learning_progress(viewport: "GLViewportWidget", payload: object) -> None:
    if not isinstance(payload, dict):
        return
    viewport._othello_book_learning_progress = dict(payload)
    line = tuple(int(move) for move in tuple(payload.get("line",())))
    explored_positions = int(payload.get("explored_positions", 0))
    remaining_depth = int(payload.get("remaining_depth", 0))
    if line:
        viewport._othello_book_learning_status_text = f"Book learning | Explored {explored_positions} | Depth {remaining_depth} | PV {_format_best_line(line, limit=6)}"
    else:
        viewport._othello_book_learning_status_text = f"Book learning | Explored {explored_positions} | Depth {remaining_depth}"
    viewport._othello_settings.set_learning_running(True, status_text=str(viewport._othello_book_learning_status_text))
    viewport._othello_render_state_cache_key = None
    viewport._othello_render_state_cache = None
    sync_hud_text(viewport)
    viewport.update()


def on_book_learning_ready(viewport: "GLViewportWidget", payload: object) -> None:
    viewport._othello_book_learning_running = False
    viewport._othello_book_learning_progress = None
    viewport._othello_render_state_cache_key = None
    viewport._othello_render_state_cache = None
    _refresh_book_summary(viewport)
    if isinstance(payload, dict) and bool(payload.get("cancelled", False)):
        viewport._othello_book_learning_status_text = "Opening book learning cancelled."
    elif isinstance(payload, dict) and bool(payload.get("ok", False)):
        result = payload.get("result")
        added_lines = int(getattr(result, "added_lines", 0))
        total_lines = int(getattr(result, "total_lines", 0))
        explored_positions = int(getattr(result, "explored_positions", 0))
        viewport._othello_book_learning_status_text = f"Opening book updated. Added {added_lines} lines, total {total_lines}, explored {explored_positions} positions."
    else:
        error_text = ""
        if isinstance(payload, dict):
            error_text = str(payload.get("error", "")).strip()
        viewport._othello_book_learning_status_text = "Opening book learning failed." if not error_text else f"Opening book learning failed: {error_text}"
    viewport._othello_settings.set_learning_running(False, status_text=str(viewport._othello_book_learning_status_text))
    viewport._othello_analysis_request_signature = None
    sync_hud_text(viewport)
    maybe_request_analysis(viewport)
    viewport.update()


def clear_state_for_space_switch(viewport: "GLViewportWidget") -> None:
    viewport._othello_ai.cancel_book_learning(emit_ready=False)
    viewport._othello_match.settle_animations()
    viewport._pending_othello_ai_result = None
    viewport._othello_ai_request_armed = False
    viewport._othello_hover_square = None
    viewport._othello_hud_signature = None
    viewport._othello_render_state_cache_key = None
    viewport._othello_render_state_cache = None
    viewport._othello_analysis = OthelloAnalysis().normalized()
    viewport._othello_analysis_request_signature = None
    viewport._othello_book_learning_running = False
    viewport._othello_book_learning_status_text = ""
    viewport._othello_book_learning_progress = None
    clear_title_flash(viewport)
    viewport._last_othello_message = ""


def maybe_request_ai(viewport: "GLViewportWidget") -> None:
    if not viewport._state.is_othello_space():
        return
    if viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead():
        return

    state = viewport._othello_match.game_state()
    if state.status != OTHELLO_GAME_STATE_AI_TURN or bool(state.thinking) or bool(viewport._othello_ai_request_armed):
        return

    viewport._othello_match.set_ai_thinking(True)
    state = viewport._othello_match.game_state()
    sync_hud_text(viewport)

    generation = int(state.match_generation)
    board = tuple(state.board)
    side = int(state.ai_side)
    difficulty = str(state.settings.difficulty)
    seed = int(state.match_generation * 257 + state.move_count * 17 + 3)
    thread_count = int(state.settings.thread_count)
    sacrifice_level = int(state.settings.sacrifice_level)
    hash_level = int(state.settings.hash_level)
    project_root = str(viewport._project_root)

    viewport._othello_ai_request_armed = True
    QTimer.singleShot(0, lambda generation=generation, board=board, side=side, difficulty=difficulty, seed=seed, project_root=project_root, thread_count=thread_count, sacrifice_level=sacrifice_level, hash_level=hash_level: dispatch_ai_request(viewport, generation=generation, board=board, side=side, difficulty=difficulty, seed=seed, project_root=project_root, thread_count=thread_count, sacrifice_level=sacrifice_level, hash_level=hash_level))


def dispatch_ai_request(viewport: "GLViewportWidget", *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int, project_root: str, thread_count: int, sacrifice_level: int, hash_level: int) -> None:
    viewport._othello_ai_request_armed = False
    if not viewport._state.is_othello_space():
        return
    if viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead():
        return

    state = viewport._othello_match.game_state()
    if int(state.match_generation) != int(generation) or state.status != OTHELLO_GAME_STATE_AI_TURN or not bool(state.thinking):
        return

    viewport._othello_ai.request_move(generation=int(generation), board=tuple(board), side=int(side), difficulty=str(difficulty), seed=int(seed), project_root=str(project_root), thread_count=int(thread_count), sacrifice_level=int(sacrifice_level), hash_level=int(hash_level))


def maybe_request_analysis(viewport: "GLViewportWidget") -> None:
    if not viewport._state.is_othello_space():
        return
    if viewport.loading_active() or viewport._overlays.dead():
        return
    if bool(viewport._othello_book_learning_running):
        return

    state = viewport._othello_match.game_state()
    if state.status not in (OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_GAME_STATE_FINISHED):
        return

    signature = (int(state.match_generation), tuple(state.board), int(state.current_turn), str(state.status), str(state.settings.difficulty), int(state.settings.sacrifice_level), int(state.settings.hash_level))
    if viewport._othello_analysis_request_signature == signature:
        return

    viewport._othello_analysis_request_signature = signature
    analysis_side = int(state.current_turn if state.status != OTHELLO_GAME_STATE_FINISHED else state.ai_side)
    analysis_seed = int(state.match_generation * 131 + state.move_count * 29 + 11)
    viewport._othello_ai.request_analysis(generation=int(state.match_generation), board=tuple(state.board), side=int(analysis_side), difficulty=str(state.settings.difficulty), seed=int(analysis_seed), project_root=str(viewport._project_root), thread_count=int(state.settings.thread_count), sacrifice_level=int(state.settings.sacrifice_level), hash_level=int(state.settings.hash_level))


def on_analysis_ready(viewport: "GLViewportWidget", generation: int, analysis: object) -> None:
    state = viewport._othello_match.game_state()
    if int(generation) != int(state.match_generation):
        return
    if isinstance(analysis, OthelloAnalysis):
        viewport._othello_analysis = analysis.normalized()
    else:
        viewport._othello_analysis = OthelloAnalysis().normalized()
    sync_hud_text(viewport)


def consume_pending_ai_result(viewport: "GLViewportWidget") -> None:
    if viewport._pending_othello_ai_result is None:
        return
    if viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead():
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
    maybe_request_analysis(viewport)


def on_ai_move_ready(viewport: "GLViewportWidget", generation: int, move_index: object) -> None:
    result = None if move_index is None else int(move_index)
    if viewport._overlays.paused() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open() or viewport._overlays.dead():
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
        maybe_request_analysis(viewport)


def handle_right_click(viewport: "GLViewportWidget") -> None:
    import ludoxel.shared.ui.viewport.controllers.interaction_controller as interaction_controller

    item_id = settings_controller.current_item_id(viewport)
    if item_id == OTHELLO_START_ITEM_ID:
        viewport._othello_match.restart_match()
        viewport._pending_othello_ai_result = None
        viewport._othello_ai_request_armed = False
        viewport._othello_analysis = OthelloAnalysis().normalized()
        viewport._othello_analysis_request_signature = None
        viewport._first_person_motion.trigger_right_swing(success=True)
        sync_hud_text(viewport)
        maybe_request_ai(viewport)
        maybe_request_analysis(viewport)
        return

    if item_id == OTHELLO_SETTINGS_ITEM_ID:
        viewport._first_person_motion.trigger_right_swing(success=True)
        interaction_controller.open_othello_settings_from_item(viewport)
