# FILE: src/maiming/presentation/widgets/viewport/gl_viewport_widget.py
from __future__ import annotations
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QMessageBox

from ....application.othello.othello_match_controller import OthelloMatchController
from ....application.session.fixed_step_runner import FixedStepRunner
from ....application.session.play_space_sessions import PlaySpaceSessions
from ....core.math.vec3 import Vec3
from ....core.math.view_angles import forward_from_yaw_pitch_deg
from ....domain.inventory.special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID
from ....domain.othello.rules import counts_for_board
from ....domain.othello.types import OTHELLO_GAME_STATE_AI_TURN, OTHELLO_GAME_STATE_FINISHED, OTHELLO_GAME_STATE_PLAYER_TURN, OTHELLO_WINNER_DRAW, SIDE_BLACK, SIDE_WHITE
from ....domain.play_space import PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO, normalize_play_space_id
from ....infrastructure.platform.qt_input_adapter import QtInputAdapter
from ....infrastructure.rendering.opengl._internal.scene.othello_scene import raycast_board_square
from ....infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from ....infrastructure.rendering.opengl.facade.othello_render_state import OthelloRenderState
from ....infrastructure.rendering.opengl.facade.player_render_state import FirstPersonRenderState, PlayerRenderState
from ...config.game_loop_params import DEFAULT_GAME_LOOP_PARAMS, GameLoopParams
from ...config.gl_surface_format import build_gl_surface_format
from ...hud.hud_controller import HudController
from ..common import hotbar_index_from_key
from ..hud.crosshair_widget import CrosshairWidget
from ..hud.hotbar_widget import HotbarWidget
from ..hud.othello_hud_widget import OthelloHudWidget
from ..overlays.death_overlay import DeathOverlay
from ..overlays.inventory_overlay import InventoryOverlay
from ..overlays.othello_settings_overlay import OthelloSettingsOverlay
from ..overlays.pause_overlay import PauseOverlay
from ..overlays.settings_overlay import SettingsOverlay
from .first_person_motion import FirstPersonMotionController
from .othello_ai_worker import OthelloAiWorker
from .view_model_visibility import view_model_visible
from .viewport_input import ViewportInput
from .viewport_overlays import OverlayRefs, ViewportOverlays
from .viewport_persistence import apply_persisted_state_if_present, save_state
from .viewport_runtime_state import ViewportRuntimeState
from .viewport_selection_state import ViewportSelectionState
from .viewport_world_upload import WorldUploadTracker

def _format_clock(seconds_remaining: float | None) -> str:
    if seconds_remaining is None:
        return "No limit"
    seconds = max(0, int(round(float(seconds_remaining))))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

class GLViewportWidget(QOpenGLWidget):
    hud_updated = pyqtSignal(object)
    fullscreen_changed = pyqtSignal(bool)

    def __init__(self, project_root: Path, parent=None, loop_params: GameLoopParams = DEFAULT_GAME_LOOP_PARAMS) -> None:
        super().__init__(parent)

        self._project_root = Path(project_root)
        self._assets_dir = self._project_root / "assets"
        self._loop = loop_params

        self._adapter = QtInputAdapter(self)
        self._inp = ViewportInput(widget=self, adapter=self._adapter)

        self._sessions = PlaySpaceSessions.create_default(seed=0)
        self._session = self._sessions.active_session()
        self._runner = FixedStepRunner(step_dt=self._loop.step_dt(), on_step=self._on_step)

        self._renderer = GLRenderer()
        self._hud = None
        self._othello_hud = OthelloHudWidget(self)
        self._othello_hud.setVisible(False)

        self._upload = WorldUploadTracker()
        self._hud_ctl = HudController()

        self._state = ViewportRuntimeState()
        self._sync_state_from_renderer_sun()
        self._first_person_motion = FirstPersonMotionController(slim_arm=True)

        self._selection_state = ViewportSelectionState()
        self._othello_match = OthelloMatchController()
        self._othello_ai = OthelloAiWorker(self)
        self._othello_ai.move_ready.connect(self._on_othello_ai_move_ready)
        self._othello_hover_square: int | None = None
        self._pending_othello_ai_result: tuple[int, int | None] | None = None
        self._othello_ai_request_armed: bool = False
        self._othello_title_flash_text: str = ""
        self._othello_title_flash_until_s: float = 0.0
        self._last_othello_message: str = ""

        self._last_paint_ms: float = 0.0
        self._last_selection_pick_ms: float = 0.0
        self._shutdown_done = False

        self._overlay = PauseOverlay(self)
        self._overlay.resume_requested.connect(self._resume_from_overlay)
        self._overlay.settings_requested.connect(self._open_settings_from_pause)
        self._overlay.play_my_world_requested.connect(lambda: self._switch_play_space(PLAY_SPACE_MY_WORLD, resume=True))
        self._overlay.play_othello_requested.connect(lambda: self._switch_play_space(PLAY_SPACE_OTHELLO, resume=True))

        self._settings = SettingsOverlay(self)
        self._settings.back_requested.connect(self._back_from_settings)
        self._settings.fov_changed.connect(self._set_fov)
        self._settings.sens_changed.connect(self._set_sens)
        self._settings.invert_x_changed.connect(self._set_invert_x)
        self._settings.invert_y_changed.connect(self._set_invert_y)
        self._settings.fullscreen_changed.connect(self._set_fullscreen)
        self._settings.hide_hud_changed.connect(self._set_hide_hud)
        self._settings.hide_hand_changed.connect(self._set_hide_hand)
        self._settings.view_bobbing_changed.connect(self._set_view_bobbing_enabled)
        self._settings.camera_shake_changed.connect(self._set_camera_shake_enabled)
        self._settings.view_bobbing_strength_changed.connect(self._set_view_bobbing_strength)
        self._settings.camera_shake_strength_changed.connect(self._set_camera_shake_strength)
        self._settings.outline_selection_changed.connect(self._set_outline_selection)
        self._settings.cloud_wireframe_changed.connect(self._set_cloud_wire)
        self._settings.clouds_enabled_changed.connect(self._set_cloud_enabled)
        self._settings.cloud_density_changed.connect(self._set_cloud_density)
        self._settings.cloud_seed_changed.connect(self._set_cloud_seed)
        self._settings.cloud_flow_direction_changed.connect(self._set_cloud_flow_direction)
        self._settings.world_wireframe_changed.connect(self._set_world_wire)
        self._settings.shadow_enabled_changed.connect(self._set_shadow_enabled)
        self._settings.sun_azimuth_changed.connect(self._set_sun_azimuth)
        self._settings.sun_elevation_changed.connect(self._set_sun_elevation)
        self._settings.creative_mode_changed.connect(self._set_creative_mode)
        self._settings.auto_jump_changed.connect(self._set_auto_jump)
        self._settings.auto_sprint_changed.connect(self._set_auto_sprint)
        self._settings.gravity_changed.connect(self._set_gravity)
        self._settings.walk_speed_changed.connect(self._set_walk_speed)
        self._settings.sprint_speed_changed.connect(self._set_sprint_speed)
        self._settings.jump_v0_changed.connect(self._set_jump_v0)
        self._settings.auto_jump_cooldown_changed.connect(self._set_auto_jump_cooldown_s)
        self._settings.fly_speed_changed.connect(self._set_fly_speed)
        self._settings.fly_ascend_speed_changed.connect(self._set_fly_ascend_speed)
        self._settings.fly_descend_speed_changed.connect(self._set_fly_descend_speed)
        self._settings.advanced_reset_requested.connect(self._reset_advanced_defaults)
        self._settings.render_distance_changed.connect(self._set_render_distance)

        self._othello_settings = OthelloSettingsOverlay(self)
        self._othello_settings.back_requested.connect(self._back_from_othello_settings)
        self._othello_settings.settings_applied.connect(self._apply_othello_settings)

        self._death = DeathOverlay(self)
        self._death.respawn_requested.connect(self._respawn)

        self._crosshair = CrosshairWidget(self)
        self._crosshair.setVisible(True)

        self._hotbar = HotbarWidget(parent=self, project_root=self._project_root, registry=self._session.block_registry)
        self._hotbar.setVisible(True)

        self._inventory = InventoryOverlay(parent=self, project_root=self._project_root, registry=self._session.block_registry)
        self._inventory.block_selected.connect(self._on_inventory_selected)
        self._inventory.hotbar_slot_selected.connect(self._select_hotbar_slot)
        self._inventory.hotbar_slot_assigned.connect(self._assign_hotbar_slot)
        self._inventory.closed.connect(self._on_inventory_closed)

        self._overlays = ViewportOverlays(refs=OverlayRefs(pause=self._overlay, settings=self._settings, othello_settings=self._othello_settings, inventory=self._inventory, death=self._death, crosshair=self._crosshair, hotbar=self._hotbar, hud_getter=lambda: self._hud, othello_hud_getter=lambda: self._othello_hud), runner=self._runner, inp=self._inp)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._sim_timer = QTimer(self)
        self._sim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._sim_timer.setInterval(int(self._effective_sim_timer_interval_ms()))
        self._sim_timer.timeout.connect(self._tick_sim)

        self._render_timer = QTimer(self)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._render_timer.setInterval(int(max(0, int(self._loop.render_timer_interval_ms))))
        self._render_timer.timeout.connect(self.update)

        self.setFormat(build_gl_surface_format())

        self._state, persisted_othello_state = apply_persisted_state_if_present(project_root=self._project_root, sessions=self._sessions, renderer=self._renderer)
        self._session = self._sessions.set_active_space(self._state.current_space_id)
        self._othello_match.set_default_settings(self._state.othello_settings)
        self._othello_match.set_game_state(persisted_othello_state)
        self._overlay.set_current_space(self._state.current_space_id)

        self._apply_runtime_to_renderer()
        self._sync_hotbar_widgets()
        self._sync_first_person_target()
        self._sync_view_model_visibility()
        self._sync_othello_hud_text()
        self._sync_gameplay_hud_visibility()

    def _for_each_session(self, fn) -> None:
        for session in self._sessions.all_sessions():
            fn(session)

    def _sync_state_from_renderer_sun(self) -> None:
        az, el = self._renderer.sun_angles()
        self._state.sun_az_deg = float(az)
        self._state.sun_el_deg = float(el)
        self._state.normalize()

    def _apply_runtime_to_renderer(self) -> None:
        self._state.normalize()
        self._renderer.set_debug_shadow(bool(self._state.debug_shadow))
        self._renderer.set_outline_selection_enabled(bool(self._state.outline_selection))
        self._renderer.set_cloud_wireframe(bool(self._state.cloud_wire))
        self._renderer.set_cloud_enabled(bool(self._state.cloud_enabled))
        self._renderer.set_cloud_density(int(self._state.cloud_density))
        self._renderer.set_cloud_seed(int(self._state.cloud_seed))
        self._renderer.set_cloud_flow_direction(str(self._state.cloud_flow_direction))
        self._renderer.set_shadow_enabled(bool(self._state.shadow_enabled))
        self._renderer.set_world_wireframe(bool(self._state.world_wire))
        self._renderer.set_sun_angles(float(self._state.sun_az_deg), float(self._state.sun_el_deg))

    def _sync_cloud_motion_pause(self) -> None:
        self._renderer.set_cloud_motion_paused(bool(self._overlays.paused()))

    def _inventory_available(self) -> bool:
        return not self._state.is_othello_space()

    def _sync_hotbar_widgets(self) -> None:
        self._state.normalize()
        slots = self._state.hotbar_snapshot()
        idx = self._state.othello_selected_hotbar_index if self._state.is_othello_space() else (
            self._state.creative_selected_hotbar_index if bool(self._state.creative_mode) else self._state.survival_selected_hotbar_index
        )
        self._inventory.set_creative_mode(bool(self._state.creative_mode and self._inventory_available()))
        self._inventory.sync_hotbar(slots=slots, selected_index=int(idx))
        self._hotbar.sync_hotbar(slots=slots, selected_index=int(idx))

    def _current_item_id(self) -> str | None:
        self._state.normalize()
        return self._state.current_item_id()

    def _current_block_id(self) -> str | None:
        self._state.normalize()
        return self._state.current_block_id()

    def _sync_view_model_visibility(self) -> None:
        visible = view_model_visible(hide_hand=bool(self._state.hide_hand))
        self._first_person_motion.set_view_model_visible(bool(visible))

    def _sync_first_person_target(self) -> None:
        self._first_person_motion.set_target_block_id(self._current_block_id())
        self._sync_view_model_visibility()

    def _select_hotbar_slot(self, slot_index: int) -> None:
        self._state.select_hotbar_index(int(slot_index))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _assign_hotbar_slot(self, slot_index: int, item_id: str) -> None:
        self._state.set_hotbar_slot(int(slot_index), str(item_id))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _cycle_hotbar(self, step: int) -> None:
        self._state.cycle_hotbar(int(step))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def save_state(self) -> None:
        self._sync_state_from_renderer_sun()
        settled_othello_state = self._othello_match.settle_animations()
        save_state(project_root=self._project_root, sessions=self._sessions, renderer=self._renderer, runtime=self._state, othello_game_state=settled_othello_state)

    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        try:
            self._sim_timer.stop()
        except Exception:
            pass
        try:
            self._render_timer.stop()
        except Exception:
            pass
        try:
            self._inp.set_mouse_capture(False)
        except Exception:
            pass
        try:
            self.save_state()
        except Exception:
            pass
        try:
            self._othello_ai.shutdown()
        except Exception:
            pass
        try:
            if self.context() is not None:
                self.makeCurrent()
                try:
                    self._renderer.destroy()
                finally:
                    self.doneCurrent()
        except Exception:
            pass

    def closeEvent(self, e) -> None:
        self.shutdown()
        super().closeEvent(e)

    def _effective_sim_timer_interval_ms(self) -> int:
        ms = int(self._loop.sim_timer_interval_ms)
        if ms > 0:
            return ms
        hz = float(self._loop.sim_hz)
        if hz <= 1e-6:
            return 1
        return max(1, int(round(1000.0 / hz)))

    def set_hud(self, hud) -> None:
        self._hud = hud
        self._hud.setParent(self)
        self._hud.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        self._sync_gameplay_hud_visibility()

    def _invalidate_selection_target(self) -> None:
        self._selection_state.invalidate()

    def fullscreen_enabled(self) -> bool:
        return bool(self._state.fullscreen)

    def _make_render_snapshot(self):
        return self._session.make_snapshot(enable_view_bobbing=bool(self._state.view_bobbing_enabled), enable_camera_shake=bool(self._state.camera_shake_enabled), view_bobbing_strength=float(self._state.view_bobbing_strength), camera_shake_strength=float(self._state.camera_shake_strength))

    @staticmethod
    def _effective_camera_from_snapshot(snapshot) -> tuple[Vec3, float, float, float, Vec3]:
        cam = snapshot.camera
        eye = Vec3(float(cam.eye_x) + float(cam.shake_tx), float(cam.eye_y) + float(cam.shake_ty), float(cam.eye_z) + float(cam.shake_tz))
        yaw_deg = float(cam.yaw_deg) + float(cam.shake_yaw_deg)
        pitch_deg = float(cam.pitch_deg) + float(cam.shake_pitch_deg)
        roll_deg = float(cam.shake_roll_deg)
        direction = forward_from_yaw_pitch_deg(float(yaw_deg), float(pitch_deg))
        return (eye, float(yaw_deg), float(pitch_deg), float(roll_deg), direction)

    def _gameplay_hud_active(self) -> bool:
        return ((not bool(self._state.hide_hud)) and (not self._overlays.dead()) and (not self._overlays.paused()) and (not self._overlays.settings_open()) and (not self._overlays.othello_settings_open()) and (not self._overlays.inventory_open()))

    def _debug_hud_active(self) -> bool:
        return bool(self._state.hud_visible) and bool(self._gameplay_hud_active())

    def _set_othello_title_flash(self, text: str, *, duration_s: float) -> None:
        body = str(text).strip()
        if not body:
            return
        self._othello_title_flash_text = body
        self._othello_title_flash_until_s = time.perf_counter() + max(0.0, float(duration_s))

    def _clear_othello_title_flash(self) -> None:
        self._othello_title_flash_text = ""
        self._othello_title_flash_until_s = 0.0

    def _track_othello_message_for_title(self, message: str) -> None:
        body = str(message).strip()
        if body == self._last_othello_message:
            return
        self._last_othello_message = body
        lower = body.lower()
        if "must pass" in lower:
            self._set_othello_title_flash(body, duration_s=1.75)
        elif "match started" in lower:
            self._set_othello_title_flash("Match started", duration_s=1.10)

    def _othello_title_text(self, *, black_count: int, white_count: int) -> str:
        if not self._state.is_othello_space():
            return ""
        state = self._othello_match.game_state()
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
        if self._othello_title_flash_text and now < float(self._othello_title_flash_until_s):
            lines.append(str(self._othello_title_flash_text))
        if bool(state.thinking):
            lines.append("AI is thinking...")

        unique: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if line and line not in seen:
                unique.append(line)
                seen.add(line)
        return "\n".join(unique)

    def _sync_othello_hud_text(self) -> None:
        if not self._state.is_othello_space():
            self._othello_hud.set_text("")
            self._othello_hud.set_title_text("")
            self._last_othello_message = ""
            self._clear_othello_title_flash()
            return

        state = self._othello_match.game_state()
        self._track_othello_message_for_title(state.message)
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
        self._othello_hud.set_text("\n".join([str(turn_text), f"Black {int(black_count)}  White {int(white_count)}", f"AI {difficulty}  You {player_color}  AI {ai_color}", f"Black clock: {_format_clock(state.black_time_remaining_s)}", f"White clock: {_format_clock(state.white_time_remaining_s)}", str(state.message)]))
        self._othello_hud.set_title_text(self._othello_title_text(black_count=int(black_count), white_count=int(white_count)))

    def _sync_gameplay_hud_visibility(self) -> None:
        show_gameplay_hud = bool(self._gameplay_hud_active())
        show_othello_hud = bool(show_gameplay_hud and self._state.is_othello_space())

        self._crosshair.setVisible(bool(show_gameplay_hud))
        self._hotbar.setVisible(bool(show_gameplay_hud))
        self._othello_hud.setVisible(bool(show_othello_hud))

        if self._hud is not None:
            self._hud.setVisible(bool(self._debug_hud_active()))
            if bool(self._debug_hud_active()):
                self._hud.raise_()

        if bool(show_gameplay_hud):
            self._hotbar.raise_()
            self._crosshair.raise_()
            if bool(show_othello_hud):
                self._othello_hud.raise_()
            if self._hud is not None and bool(self._debug_hud_active()):
                self._hud.raise_()

    def _set_dead_overlay(self, on: bool) -> None:
        self._overlays.set_dead(bool(on))
        self._sync_gameplay_hud_visibility()

    def _set_paused_overlay(self, on: bool) -> None:
        self._overlays.set_paused(bool(on))
        self._sync_gameplay_hud_visibility()

    def _set_settings_overlay(self, on: bool) -> None:
        self._overlays.set_settings_open(bool(on))
        self._sync_gameplay_hud_visibility()

    def _set_othello_settings_overlay(self, on: bool) -> None:
        self._overlays.set_othello_settings_open(bool(on))
        self._sync_gameplay_hud_visibility()

    def _set_inventory_overlay(self, on: bool) -> None:
        if bool(on) and not self._inventory_available():
            return
        self._overlays.set_inventory_open(bool(on))
        self._sync_gameplay_hud_visibility()

    def initializeGL(self) -> None:
        try:
            self._renderer.initialize(self._assets_dir, block_registry=self._session.block_registry)
        except Exception as exc:
            try:
                self._sim_timer.stop()
            except Exception:
                pass
            try:
                self._render_timer.stop()
            except Exception:
                pass
            try:
                self._inp.set_mouse_capture(False)
            except Exception:
                pass
            QMessageBox.critical(self, "OpenGL 4.3 initialization failed", str(exc).strip() if str(exc).strip() else "Unknown OpenGL initialization error.")
            raise

        ctx = self.context()
        if ctx is not None:
            try:
                self._state.vsync_on = int(ctx.format().swapInterval()) > 0
            except Exception:
                self._state.vsync_on = False

        self._apply_runtime_to_renderer()
        self._sync_hotbar_widgets()
        self._sync_cloud_motion_pause()
        self._sync_othello_hud_text()
        self._sync_gameplay_hud_visibility()
        self._runner.start()
        self._sim_timer.start()
        self._render_timer.start()

    def resizeGL(self, w: int, h: int) -> None:
        if self._hud is not None:
            self._hud.setGeometry(0, 0, max(1, w), max(1, h))

        self._othello_hud.setGeometry(0, 0, max(1, w), max(1, h))
        self._overlay.setGeometry(0, 0, max(1, w), max(1, h))
        self._settings.setGeometry(0, 0, max(1, w), max(1, h))
        self._othello_settings.setGeometry(0, 0, max(1, w), max(1, h))
        self._crosshair.setGeometry(0, 0, max(1, w), max(1, h))
        self._hotbar.setGeometry(0, 0, max(1, w), max(1, h))
        self._inventory.setGeometry(0, 0, max(1, w), max(1, h))
        self._death.setGeometry(0, 0, max(1, w), max(1, h))

        if self._overlays.dead():
            self._death.raise_()
        elif self._overlays.othello_settings_open():
            self._othello_settings.raise_()
        elif self._overlays.settings_open():
            self._settings.raise_()
        elif self._overlays.paused():
            self._overlay.raise_()
        elif self._overlays.inventory_open():
            self._inventory.raise_()
        else:
            self._sync_gameplay_hud_visibility()
            return

        self._sync_gameplay_hud_visibility()

    def _build_othello_render_state(self) -> OthelloRenderState | None:
        if not self._state.is_othello_space():
            return None
        game_state = self._othello_match.game_state()
        legal_moves = game_state.legal_moves if game_state.status == OTHELLO_GAME_STATE_PLAYER_TURN else ()
        return OthelloRenderState(enabled=True, board=tuple(game_state.board), legal_move_indices=tuple(int(index) for index in tuple(legal_moves)), hover_square_index=self._othello_hover_square, last_move_index=game_state.last_move_index, animations=tuple(game_state.animations))

    def _refresh_othello_hover_square(self, snapshot) -> None:
        self._othello_hover_square = None
        if not self._state.is_othello_space() or self._overlays.any_modal_open():
            return

        game_state = self._othello_match.game_state()
        if game_state.status != OTHELLO_GAME_STATE_PLAYER_TURN:
            return

        render_eye, _render_yaw_deg, _render_pitch_deg, _render_roll_deg, render_direction = self._effective_camera_from_snapshot(snapshot)
        square_index = raycast_board_square(render_eye, render_direction)
        if square_index is None or int(square_index) not in set(game_state.legal_moves):
            return
        self._othello_hover_square = int(square_index)

    def paintGL(self) -> None:
        paint_t0 = time.perf_counter()
        self._hud_ctl.on_render_frame()

        snap = self._make_render_snapshot()
        eye = Vec3(snap.camera.eye_x, snap.camera.eye_y, snap.camera.eye_z)
        render_eye, render_yaw_deg, render_pitch_deg, render_roll_deg, _render_direction = self._effective_camera_from_snapshot(snap)

        self._upload.upload_if_needed(world=self._session.world, renderer=self._renderer, eye=eye, render_distance_chunks=int(self._state.render_distance_chunks))

        if self._state.is_othello_space():
            self._last_selection_pick_ms = 0.0
            self._invalidate_selection_target()
            self._renderer.clear_selection()
            self._refresh_othello_hover_square(snap)
        else:
            self._othello_hover_square = None
            self._last_selection_pick_ms = self._selection_state.refresh(session=self._session, reach=float(self._state.reach), eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg))
            selection_target = self._selection_state.target()
            if selection_target is None:
                self._renderer.clear_selection()
            else:
                hx, hy, hz, st = selection_target

                def get_state(x: int, y: int, z: int) -> str | None:
                    return self._session.world.blocks.get((int(x), int(y), int(z)))

                self._renderer.set_selection_target(x=int(hx), y=int(hy), z=int(hz), state_str=str(st), get_state=get_state, world_revision=int(self._session.world.revision))

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        cam = snap.camera
        pl = snap.player_model
        motion = self._first_person_motion.sample()
        visible_def = None if motion.visible_block_id is None else self._session.block_registry.get(str(motion.visible_block_id))
        first_person = FirstPersonRenderState(visible_block_id=motion.visible_block_id, visible_block_kind=None if visible_def is None else str(visible_def.kind), target_block_id=motion.target_block_id, equip_progress=float(motion.equip_progress), prev_equip_progress=float(motion.prev_equip_progress), swing_progress=float(motion.swing_progress), prev_swing_progress=float(motion.prev_swing_progress), show_arm=bool(motion.show_arm), show_view_model=bool(motion.show_view_model), slim_arm=bool(motion.slim_arm), view_bob_x=float(pl.first_person_tx), view_bob_y=float(pl.first_person_ty), view_bob_z=float(pl.first_person_tz), view_bob_yaw_deg=float(pl.first_person_yaw_deg), view_bob_pitch_deg=float(pl.first_person_pitch_deg), view_bob_roll_deg=float(pl.first_person_roll_deg))
        player_state = PlayerRenderState(base_x=float(pl.base_x), base_y=float(pl.base_y), base_z=float(pl.base_z), body_yaw_deg=float(pl.body_yaw_deg), head_yaw_deg=float(pl.head_yaw_deg), head_pitch_deg=float(pl.head_pitch_deg), limb_phase_rad=float(pl.limb_phase_rad), limb_swing_amount=float(pl.limb_swing_amount), crouch_amount=float(pl.crouch_amount), is_first_person=bool(pl.is_first_person), first_person=first_person)

        self._renderer.render(w=fb_w, h=fb_h, eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg), fov_deg=float(cam.fov_deg), render_distance_chunks=int(self._state.render_distance_chunks), player_state=player_state, othello_state=self._build_othello_render_state())
        self._last_paint_ms = float((time.perf_counter() - paint_t0) * 1000.0)

    def _tick_sim(self) -> None:
        if self._overlays.dead() or self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open():
            return
        self._runner.update()

    def _sync_settings_values(self) -> None:
        self._sync_state_from_renderer_sun()
        self._settings.sync_values(fov_deg=self._session.settings.fov_deg, sens_deg_per_px=self._session.settings.mouse_sens_deg_per_px, inv_x=self._state.invert_x, inv_y=self._state.invert_y, fullscreen=self._state.fullscreen, hide_hud=self._state.hide_hud, hide_hand=self._state.hide_hand, view_bobbing_enabled=self._state.view_bobbing_enabled, camera_shake_enabled=self._state.camera_shake_enabled, view_bobbing_strength=float(self._state.view_bobbing_strength), camera_shake_strength=float(self._state.camera_shake_strength), outline_selection=self._state.outline_selection, cloud_wire=self._state.cloud_wire, clouds_enabled=self._state.cloud_enabled, cloud_density=int(self._state.cloud_density), cloud_seed=int(self._state.cloud_seed), cloud_flow_direction=str(self._state.cloud_flow_direction), world_wire=self._state.world_wire, shadow_enabled=self._state.shadow_enabled, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, creative_mode=self._state.creative_mode, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, gravity=float(self._session.settings.movement.gravity), walk_speed=float(self._session.settings.movement.walk_speed), sprint_speed=float(self._session.settings.movement.sprint_speed), jump_v0=float(self._session.settings.movement.jump_v0), auto_jump_cooldown_s=float(self._session.settings.movement.auto_jump_cooldown_s), fly_speed=float(self._session.settings.movement.fly_speed), fly_ascend_speed=float(self._session.settings.movement.fly_ascend_speed), fly_descend_speed=float(self._session.settings.movement.fly_descend_speed), render_distance_chunks=int(self._state.render_distance_chunks))

    def _sync_othello_settings_values(self) -> None:
        self._othello_settings.sync_values(self._state.othello_settings)

    def _respawn(self) -> None:
        self._session.respawn()
        self._invalidate_selection_target()
        self._renderer.clear_selection()
        self._set_dead_overlay(False)

    def _resume_from_overlay(self) -> None:
        self._set_paused_overlay(False)
        self._sync_cloud_motion_pause()

    def _switch_play_space(self, space_id: str, *, resume: bool = False) -> None:
        normalized = normalize_play_space_id(space_id)
        if normalized == normalize_play_space_id(self._state.current_space_id):
            if resume:
                self._resume_from_overlay()
            return

        self._othello_match.settle_animations()
        self._pending_othello_ai_result = None
        self._othello_ai_request_armed = False
        self._clear_othello_title_flash()
        self._last_othello_message = ""
        self._state.current_space_id = normalized
        self._state.normalize()
        self._session = self._sessions.set_active_space(normalized)
        self._overlay.set_current_space(normalized)
        self._upload.reset(self._renderer)
        self._invalidate_selection_target()
        self._renderer.clear_selection()
        self._sync_hotbar_widgets()
        self._sync_first_person_target()
        self._sync_othello_hud_text()
        self._sync_gameplay_hud_visibility()

        if resume:
            self._resume_from_overlay()

        self._maybe_request_othello_ai()

    def _open_settings_from_pause(self) -> None:
        self._sync_settings_values()
        self._set_settings_overlay(True)
        self._sync_cloud_motion_pause()

    def _back_from_settings(self) -> None:
        self._sync_settings_values()
        self._set_settings_overlay(False)
        self._sync_cloud_motion_pause()

    def _open_othello_settings_from_item(self) -> None:
        self._sync_othello_settings_values()
        self._set_othello_settings_overlay(True)
        self._sync_cloud_motion_pause()

    def _back_from_othello_settings(self) -> None:
        self._set_othello_settings_overlay(False)
        self._sync_cloud_motion_pause()

    def _apply_othello_settings(self, settings) -> None:
        self._state.othello_settings = settings.normalized()
        self._state.normalize()
        self._othello_match.set_default_settings(self._state.othello_settings)
        self._sync_othello_hud_text()
        self.save_state()

    def _set_fov(self, fov: float) -> None:
        self._for_each_session(lambda session: session.settings.set_fov(float(fov)))

    def _set_sens(self, sens: float) -> None:
        self._for_each_session(lambda session: session.settings.set_mouse_sens(float(sens)))

    def _set_invert_x(self, on: bool) -> None:
        self._state.invert_x = bool(on)

    def _set_invert_y(self, on: bool) -> None:
        self._state.invert_y = bool(on)

    def _set_fullscreen(self, on: bool) -> None:
        on = bool(on)
        if on == bool(self._state.fullscreen):
            return
        self._state.fullscreen = bool(on)
        self.fullscreen_changed.emit(bool(self._state.fullscreen))

    def _set_hide_hud(self, on: bool) -> None:
        self._state.hide_hud = bool(on)
        self._sync_gameplay_hud_visibility()

    def _set_hide_hand(self, on: bool) -> None:
        self._state.hide_hand = bool(on)
        self._sync_view_model_visibility()

    def _set_view_bobbing_enabled(self, on: bool) -> None:
        self._state.view_bobbing_enabled = bool(on)

    def _set_camera_shake_enabled(self, on: bool) -> None:
        self._state.camera_shake_enabled = bool(on)

    def _set_view_bobbing_strength(self, strength: float) -> None:
        self._state.view_bobbing_strength = float(strength)
        self._state.normalize()

    def _set_camera_shake_strength(self, strength: float) -> None:
        self._state.camera_shake_strength = float(strength)
        self._state.normalize()

    def _set_outline_selection(self, on: bool) -> None:
        self._state.outline_selection = bool(on)
        self._renderer.set_outline_selection_enabled(bool(self._state.outline_selection))

    def _set_cloud_wire(self, on: bool) -> None:
        self._state.cloud_wire = bool(on)
        self._renderer.set_cloud_wireframe(bool(self._state.cloud_wire))

    def _set_cloud_enabled(self, on: bool) -> None:
        self._state.cloud_enabled = bool(on)
        self._renderer.set_cloud_enabled(bool(self._state.cloud_enabled))

    def _set_cloud_density(self, v: int) -> None:
        self._state.cloud_density = int(v)
        self._state.normalize()
        self._renderer.set_cloud_density(int(self._state.cloud_density))

    def _set_cloud_seed(self, v: int) -> None:
        self._state.cloud_seed = int(v)
        self._state.normalize()
        self._renderer.set_cloud_seed(int(self._state.cloud_seed))

    def _set_cloud_flow_direction(self, direction: str) -> None:
        self._state.cloud_flow_direction = str(direction)
        self._state.normalize()
        self._renderer.set_cloud_flow_direction(str(self._state.cloud_flow_direction))

    def _set_world_wire(self, on: bool) -> None:
        self._state.world_wire = bool(on)
        self._renderer.set_world_wireframe(bool(self._state.world_wire))

    def _set_shadow_enabled(self, on: bool) -> None:
        self._state.shadow_enabled = bool(on)
        self._renderer.set_shadow_enabled(bool(self._state.shadow_enabled))

    def _set_sun_azimuth(self, az_deg: float) -> None:
        self._state.sun_az_deg = float(az_deg)
        self._state.normalize()
        self._renderer.set_sun_angles(float(self._state.sun_az_deg), float(self._state.sun_el_deg))

    def _set_sun_elevation(self, el_deg: float) -> None:
        self._state.sun_el_deg = float(el_deg)
        self._state.normalize()
        self._renderer.set_sun_angles(float(self._state.sun_az_deg), float(self._state.sun_el_deg))

    def _set_creative_mode(self, on: bool) -> None:
        self._state.creative_mode = bool(on)
        if not bool(self._state.creative_mode):
            self._for_each_session(lambda session: setattr(session.player, "flying", False))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _set_auto_jump(self, on: bool) -> None:
        self._state.auto_jump_enabled = bool(on)

    def _set_auto_sprint(self, on: bool) -> None:
        self._state.auto_sprint_enabled = bool(on)

    def _set_gravity(self, gravity: float) -> None:
        self._for_each_session(lambda session: session.settings.set_gravity(float(gravity)))

    def _set_walk_speed(self, walk_speed: float) -> None:
        self._for_each_session(lambda session: session.settings.set_walk_speed(float(walk_speed)))

    def _set_sprint_speed(self, sprint_speed: float) -> None:
        self._for_each_session(lambda session: session.settings.set_sprint_speed(float(sprint_speed)))

    def _set_jump_v0(self, jump_v0: float) -> None:
        self._for_each_session(lambda session: session.settings.set_jump_v0(float(jump_v0)))

    def _set_auto_jump_cooldown_s(self, cooldown_s: float) -> None:
        self._for_each_session(lambda session: session.settings.set_auto_jump_cooldown_s(float(cooldown_s)))

    def _set_fly_speed(self, fly_speed: float) -> None:
        self._for_each_session(lambda session: session.settings.set_fly_speed(float(fly_speed)))

    def _set_fly_ascend_speed(self, fly_ascend_speed: float) -> None:
        self._for_each_session(lambda session: session.settings.set_fly_ascend_speed(float(fly_ascend_speed)))

    def _set_fly_descend_speed(self, fly_descend_speed: float) -> None:
        self._for_each_session(lambda session: session.settings.set_fly_descend_speed(float(fly_descend_speed)))

    def _reset_advanced_defaults(self) -> None:
        self._for_each_session(lambda session: session.settings.reset_advanced_movement_defaults())
        self._sync_settings_values()

    def _set_render_distance(self, v: int) -> None:
        self._state.render_distance_chunks = int(v)
        self._state.normalize()

    def _maybe_request_othello_ai(self) -> None:
        if not self._state.is_othello_space():
            return
        if self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open() or self._overlays.dead():
            return
        state = self._othello_match.game_state()
        if state.status != OTHELLO_GAME_STATE_AI_TURN or bool(state.thinking) or bool(self._othello_ai_request_armed):
            return
        self._othello_match.set_ai_thinking(True)
        state = self._othello_match.game_state()
        self._sync_othello_hud_text()
        generation = int(state.match_generation)
        board = tuple(state.board)
        side = int(state.ai_side)
        difficulty = str(state.settings.difficulty)
        seed = int(state.match_generation * 257 + state.move_count * 17 + 3)
        self._othello_ai_request_armed = True
        QTimer.singleShot(0, lambda generation=generation, board=board, side=side, difficulty=difficulty, seed=seed: self._dispatch_othello_ai_request(generation, board, side, difficulty, seed))

    def _dispatch_othello_ai_request(self, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int) -> None:
        self._othello_ai_request_armed = False
        if not self._state.is_othello_space():
            return
        if self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open() or self._overlays.dead():
            return
        state = self._othello_match.game_state()
        if int(state.match_generation) != int(generation) or state.status != OTHELLO_GAME_STATE_AI_TURN or (not bool(state.thinking)):
            return
        self._othello_ai.request_move(generation=int(generation), board=tuple(board), side=int(side), difficulty=str(difficulty), seed=int(seed))

    def _consume_pending_othello_ai_result(self) -> None:
        if self._pending_othello_ai_result is None:
            return
        if self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open() or self._overlays.dead():
            return
        generation, move_index = self._pending_othello_ai_result
        self._pending_othello_ai_result = None
        self._apply_othello_ai_result(int(generation), move_index)

    def _apply_othello_ai_result(self, generation: int, move_index: int | None) -> None:
        state = self._othello_match.game_state()
        if int(generation) != int(state.match_generation) or state.status != OTHELLO_GAME_STATE_AI_TURN:
            return
        self._othello_ai_request_armed = False
        self._othello_match.submit_ai_move(move_index)
        self._sync_othello_hud_text()

    def _on_othello_ai_move_ready(self, generation: int, move_index: object) -> None:
        result = None if move_index is None else int(move_index)
        if self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open() or self._overlays.dead():
            self._pending_othello_ai_result = (int(generation), result)
            return
        self._apply_othello_ai_result(int(generation), result)

    def _on_inventory_selected(self, block_id: str) -> None:
        if not bool(self._state.creative_mode) or not self._inventory_available():
            return
        active_index = int(self._state.creative_selected_hotbar_index if bool(self._state.creative_mode) else self._state.survival_selected_hotbar_index)
        self._state.set_hotbar_slot(int(active_index), str(block_id))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _on_inventory_closed(self) -> None:
        self._set_inventory_overlay(False)

    def _on_step(self, dt: float) -> None:
        self._consume_pending_othello_ai_result()

        self._inp.poll_relative_mouse_delta()
        fr, md = self._inp.consume(invert_x=self._state.invert_x, invert_y=self._state.invert_y)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        sprint = bool(fr.sprint)
        if bool(self._state.auto_sprint_enabled) and float(fr.move_f) > 1e-6 and (not bool(fr.crouch)):
            sprint = True

        jump_started = self._session.step(dt=float(dt), move_f=fr.move_f, move_s=fr.move_s, jump_held=bool(fr.jump_held), jump_pressed=bool(fr.jump_pressed), sprint=bool(sprint), crouch=bool(fr.crouch), mdx=float(md.dx), mdy=float(md.dy), creative_mode=bool(self._state.creative_mode), auto_jump_enabled=bool(self._state.auto_jump_enabled))
        self._sync_first_person_target()
        self._first_person_motion.update(float(dt))
        self._hud_ctl.on_sim_step(dt=float(dt), player=self._session.player, jump_started=bool(jump_started))

        if self._state.is_othello_space():
            self._othello_match.tick(float(dt), paused=False)
            self._sync_othello_hud_text()
            self._maybe_request_othello_ai()

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        if not self._hud_ctl.should_emit() or not bool(self._debug_hud_active()):
            return

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        payload = self._hud_ctl.build_payload(session=self._session, renderer=self._renderer, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, creative_mode=self._state.creative_mode, flying=bool(self._session.player.flying), inventory_open=self._overlays.inventory_open(), selected_block_id=self._current_item_id() or "", reach=self._state.reach, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, shadow_enabled=self._state.shadow_enabled, world_wire=self._state.world_wire, cloud_wire=self._state.cloud_wire, cloud_enabled=self._state.cloud_enabled, cloud_density=self._state.cloud_density, cloud_seed=self._state.cloud_seed, debug_shadow=self._state.debug_shadow, fb_w=fb_w, fb_h=fb_h, dpr=dpr, vsync_on=self._state.vsync_on, render_timer_interval_ms=int(self._render_timer.interval()), sim_hz=float(self._loop.sim_hz), render_distance_chunks=int(self._state.render_distance_chunks), paint_ms=float(self._last_paint_ms), selection_pick_ms=float(self._last_selection_pick_ms))
        self.hud_updated.emit(payload)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        hotbar_idx = hotbar_index_from_key(int(e.key()))
        if hotbar_idx is not None and (not self._overlays.paused()) and (not self._overlays.dead()) and (not self._overlays.settings_open()) and (not self._overlays.othello_settings_open()):
            if not self._overlays.inventory_open():
                self._select_hotbar_slot(int(hotbar_idx))
                return

        if int(e.key()) == int(Qt.Key.Key_F4):
            self._state.debug_shadow = not bool(self._state.debug_shadow)
            self._renderer.set_debug_shadow(bool(self._state.debug_shadow))
            return

        if int(e.key()) == int(Qt.Key.Key_F3):
            self._state.hud_visible = not bool(self._state.hud_visible)
            self._sync_gameplay_hud_visibility()
            return

        if int(e.key()) == int(Qt.Key.Key_Escape):
            if self._overlays.dead():
                return
            if self._overlays.inventory_open():
                self._set_inventory_overlay(False)
                return
            if self._overlays.othello_settings_open():
                self._back_from_othello_settings()
                return
            if self._overlays.settings_open():
                self._back_from_settings()
                return
            if self._overlays.paused():
                self._set_paused_overlay(False)
                self._sync_cloud_motion_pause()
            else:
                self._sync_settings_values()
                self._overlay.set_current_space(self._state.current_space_id)
                self._set_paused_overlay(True)
                self._sync_cloud_motion_pause()
            return

        if int(e.key()) == int(Qt.Key.Key_B) and (not self._overlays.paused()) and (not self._overlays.dead()):
            self._set_creative_mode(not self._state.creative_mode)
            self._sync_settings_values()
            return

        if int(e.key()) == int(Qt.Key.Key_E) and (not self._overlays.paused()) and (not self._overlays.dead()):
            if self._inventory_available():
                self._set_inventory_overlay(not self._overlays.inventory_open())
            return

        if (not self._overlays.paused()) and (not self._overlays.inventory_open()) and (not self._overlays.dead()) and (not self._overlays.othello_settings_open()):
            self._inp.on_key_press(e)

        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open():
            super().wheelEvent(e)
            return

        dy = int(e.angleDelta().y())
        if dy > 0:
            self._cycle_hotbar(-1)
            e.accept()
            return
        if dy < 0:
            self._cycle_hotbar(1)
            e.accept()
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)

        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open():
            super().mousePressEvent(e)
            return

        if not self._inp.captured():
            self._inp.set_mouse_capture(True)
            super().mousePressEvent(e)
            return

        snap = self._make_render_snapshot()
        render_eye, _render_yaw_deg, _render_pitch_deg, _render_roll_deg, render_direction = self._effective_camera_from_snapshot(snap)

        if self._state.is_othello_space():
            if e.button() == Qt.MouseButton.LeftButton:
                self._first_person_motion.trigger_left_swing()
                square_index = raycast_board_square(render_eye, render_direction)
                if square_index is not None and self._othello_match.submit_player_move(int(square_index)):
                    self._sync_othello_hud_text()
                    self._maybe_request_othello_ai()
            elif e.button() == Qt.MouseButton.RightButton:
                item_id = self._current_item_id()
                if item_id == OTHELLO_START_ITEM_ID:
                    self._othello_match.restart_match()
                    self._pending_othello_ai_result = None
                    self._othello_ai_request_armed = False
                    self._first_person_motion.trigger_right_swing(success=True)
                    self._sync_othello_hud_text()
                    self._maybe_request_othello_ai()
                elif item_id == OTHELLO_SETTINGS_ITEM_ID:
                    self._first_person_motion.trigger_right_swing(success=True)
                    self._open_othello_settings_from_item()
            super().mousePressEvent(e)
            return

        if e.button() == Qt.MouseButton.LeftButton:
            self._session.break_block(reach=float(self._state.reach), origin=render_eye, direction=render_direction)
            self._first_person_motion.trigger_left_swing()
            self._invalidate_selection_target()
        elif e.button() == Qt.MouseButton.RightButton:
            success = self._session.place_block(block_id=self._current_block_id(), reach=float(self._state.reach), crouching=bool(self._inp.crouch_held()), origin=render_eye, direction=render_direction)
            self._first_person_motion.trigger_right_swing(success=bool(success))
            if bool(success):
                self._invalidate_selection_target()

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open() or (not self._inp.captured()):
            super().mouseMoveEvent(e)
            return
        e.accept()
        return