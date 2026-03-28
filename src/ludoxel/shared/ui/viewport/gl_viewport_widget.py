# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QImage, QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QMessageBox

from ....application.runtime.context.play_space_context import PlaySpaceContext
from ....application.runtime.state.runtime_preferences import RuntimePreferences
from ....application.runtime.tasks.fixed_step_runner import FixedStepRunner
from ....application.runtime.tasks.state_persistence import apply_persisted_state_if_present, save_state
from ....application.audio import AudioManager, PLAYER_EVENT_LAND, PLAYER_EVENT_STEP

from ....features.othello.application.othello_match_controller import OthelloMatchController
from ....features.othello.domain.engine.ai_worker import OthelloAiWorker
from ....features.othello.domain.game.types import OthelloAnalysis
from ....features.othello.ui.hud_widget import OthelloHudWidget
from ....features.othello.ui.settings_overlay import OthelloSettingsOverlay
from ....features.othello.ui.viewport import othello_controller as othello_controller

from ...math.vec3 import Vec3
from ...math.view_angles import forward_from_yaw_pitch_deg

from ...opengl.runtime.gl_renderer import GLRenderer
from ...opengl.runtime.world_upload_tracker import WorldUploadTracker
from ...rendering.block_break_particles import advance_block_break_particles, render_samples_from_block_break_particles
from ...rendering.third_person_camera import resolve_camera
from ...rendering.first_person_motion import FirstPersonMotionController
from ...rendering.player_skin import PLAYER_SKIN_KIND_ALEX, load_player_skin_image
from ...rendering.player_render_state_composer import compose_player_render_state

from ..qt_input_adapter import QtInputAdapter

from ..hud.hud_controller import HudController
from ..hud.crosshair_widget import CrosshairWidget
from ..hud.hotbar_widget import HotbarWidget
from ..overlays.death_overlay import DeathOverlay
from ..overlays.inventory_overlay import InventoryOverlay
from ..overlays.pause_overlay import PauseOverlay
from ..settings.settings_overlay import SettingsOverlay
from ..config.game_loop_params import DEFAULT_GAME_LOOP_PARAMS, GameLoopParams
from ..config.gl_surface_format import build_gl_surface_format
from .controllers import interaction_controller, settings_controller

from .runtime.frame_sync import ViewportFrameSync
from .runtime.input_controller import ViewportInput
from .runtime.overlay_controller import OverlayRefs, ViewportOverlays
from .runtime.selection_state import ViewportSelectionState


class GLViewportWidget(QOpenGLWidget):
    hud_updated = pyqtSignal(object)
    fullscreen_changed = pyqtSignal(bool)
    loading_state_changed = pyqtSignal(bool)
    loading_status_changed = pyqtSignal(str)
    loading_finished = pyqtSignal()

    def __init__(self, project_root: Path, parent=None, loop_params: GameLoopParams=DEFAULT_GAME_LOOP_PARAMS) -> None:
        super().__init__(parent)

        self._project_root = Path(project_root)
        self._assets_dir = self._project_root / "assets"
        self._loop = loop_params

        self._adapter = QtInputAdapter(self)
        self._inp = ViewportInput(widget=self, adapter=self._adapter)

        self._sessions = PlaySpaceContext.create_default(seed=0)
        self._session = self._sessions.active_session()
        self._runner = FixedStepRunner(step_dt=self._loop.step_dt(), on_step=self._on_step)

        self._renderer = GLRenderer()
        self._hud = None
        self._othello_hud = OthelloHudWidget(self)
        self._othello_hud.setVisible(False)

        self._upload = WorldUploadTracker()
        self._hud_ctl = HudController()

        self._state = RuntimePreferences()
        settings_controller.sync_state_from_renderer_sun(self)
        self._first_person_motion = FirstPersonMotionController(slim_arm=True)

        self._selection_state = ViewportSelectionState()
        self._othello_match = OthelloMatchController()
        self._othello_ai = OthelloAiWorker(self)
        self._othello_hover_square: int | None = None
        self._pending_othello_ai_result: tuple[int, int | None] | None = None
        self._othello_ai_request_armed: bool = False
        self._othello_title_flash_text: str = ""
        self._othello_title_flash_until_s: float = 0.0
        self._last_othello_message: str = ""
        self._othello_hud_signature: tuple[object, ...] | None = None
        self._othello_render_state_cache_key: tuple[object, ...] | None = None
        self._othello_render_state_cache = None
        self._othello_analysis = OthelloAnalysis().normalized()
        self._othello_analysis_request_signature: tuple[object, ...] | None = None
        self._othello_book_learning_running: bool = False
        self._othello_book_learning_status_text: str = ""
        self._othello_book_summary_text: str = ""
        self._othello_book_learning_progress: dict[str, object] | None = None
        self._othello_last_passive_hud_sync_s: float = 0.0

        self._last_paint_ms: float = 0.0
        self._last_selection_pick_ms: float = 0.0
        self._shutdown_done = False
        self._gl_initialized = False
        self._runtime_active = False
        self._frame_sync = ViewportFrameSync()
        self._player_skin_image = QImage()
        self._pause_preview_cache_key: tuple[object, ...] | None = None
        self._pause_preview_frame = QImage()
        self._block_break_particles = ()
        self._left_mouse_held: bool = False
        self._right_mouse_held: bool = False
        self._left_mouse_repeat_due_s: float = 0.0
        self._right_mouse_repeat_due_s: float = 0.0
        self._right_mouse_repeat_enabled: bool = False
        app = QGuiApplication.instance()
        self._application_active = bool(app is None or app.applicationState() == Qt.ApplicationState.ApplicationActive)

        self._overlay = PauseOverlay(self)
        self._settings = SettingsOverlay(None, as_window=True)
        self._othello_settings = OthelloSettingsOverlay(None, as_window=True)
        self._death = DeathOverlay(self)

        self._crosshair = CrosshairWidget(self)
        self._crosshair.setVisible(False)

        self._hotbar = HotbarWidget(parent=self, project_root=self._project_root, registry=self._session.block_registry)
        self._hotbar.setVisible(False)

        self._inventory = InventoryOverlay(parent=self, project_root=self._project_root, registry=self._session.block_registry)

        self._overlays = ViewportOverlays(refs=OverlayRefs(pause=self._overlay, settings=self._settings, othello_settings=self._othello_settings, inventory=self._inventory, death=self._death, crosshair=self._crosshair, hotbar=self._hotbar, hud_getter=lambda: self._hud, othello_hud_getter=lambda: self._othello_hud), runner=self._runner, inp=self._inp)
        self._overlay.preview_changed.connect(self._invalidate_pause_preview_cache)
        self._overlay.preview_changed.connect(self.update)
        settings_controller.bind_settings_overlay(self)
        othello_controller.bind_othello_controls(self)
        interaction_controller.bind_overlay_actions(self)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

        self._sim_timer = QTimer(self)
        self._sim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._sim_timer.setInterval(int(self._effective_sim_timer_interval_ms()))
        self._sim_timer.timeout.connect(self._tick_sim)

        self._render_timer = QTimer(self)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._render_timer.setInterval(int(self._effective_render_timer_interval_ms()))
        self._render_timer.timeout.connect(self.update)
        self.frameSwapped.connect(self._on_frame_swapped)

        self.setFormat(build_gl_surface_format(vsync_on=False))

        self._state, persisted_othello_state = apply_persisted_state_if_present(project_root=self._project_root, sessions=self._sessions, renderer=self._renderer)
        self._session = self._sessions.set_active_space(self._state.current_space_id)
        self._othello_match.set_default_settings(self._state.othello_settings)
        self._othello_match.set_game_state(persisted_othello_state)
        self._overlay.set_current_space(self._state.current_space_id)
        self._audio = AudioManager(project_root=self._project_root, block_registry=self._session.block_registry, parent=self)

        settings_controller.apply_runtime_to_renderer(self)
        settings_controller.sync_input_bindings(self)
        settings_controller.sync_audio_preferences(self)
        settings_controller.sync_hotbar_widgets(self)
        settings_controller.sync_crosshair_widgets(self)
        settings_controller.sync_player_skin(self)
        settings_controller.sync_first_person_target(self)
        settings_controller.sync_view_model_visibility(self)
        othello_controller.sync_settings_values(self)
        othello_controller.sync_hud_text(self)
        self._sync_gameplay_hud_visibility()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state_changed)

    def _for_each_session(self, fn) -> None:
        for session in self._sessions.all_sessions():
            fn(session)

    def record_host_window_geometry(self, *, left: int | None, top: int | None, width: int, height: int, screen_name: str) -> None:
        self._state.window_left = None if left is None else int(left)
        self._state.window_top = None if top is None else int(top)
        self._state.window_width = int(width)
        self._state.window_height = int(height)
        self._state.window_screen_name = str(screen_name or "")
        self._state.normalize()

    def _push_player_skin_to_renderer(self, *, context_current: bool=False) -> None:
        if self._player_skin_image.isNull() or self.context() is None:
            return
        if bool(context_current):
            self._renderer.set_player_skin_image(self._player_skin_image)
            return
        if not bool(self._gl_initialized):
            return
        self.makeCurrent()
        try:
            self._renderer.set_player_skin_image(self._player_skin_image)
        finally:
            self.doneCurrent()
        self.update()

    def _sync_player_skin_design(self, *, push_to_renderer: bool=False, context_current: bool=False) -> None:
        try:
            image = load_player_skin_image(self._project_root, kind=self._state.player_skin_kind)
        except Exception:
            self._state.player_skin_kind = PLAYER_SKIN_KIND_ALEX
            self._state.normalize()
            image = load_player_skin_image(self._project_root, kind=self._state.player_skin_kind)

        self._player_skin_image = QImage(image)
        self._overlay.set_player_skin(self._player_skin_image, slim_arm=True)
        self._invalidate_pause_preview_cache()
        if bool(push_to_renderer):
            self._push_player_skin_to_renderer(context_current=bool(context_current))

    def save_state(self) -> None:
        settings_controller.sync_state_from_renderer_sun(self)
        settled_othello_state = self._othello_match.settle_animations()
        save_state(project_root=self._project_root, sessions=self._sessions, renderer=self._renderer, runtime=self._state, othello_game_state=settled_othello_state)

    def loading_status_text(self) -> str:
        return self._frame_sync.loading.status_text()

    def loading_active(self) -> bool:
        return bool(self._frame_sync.loading.active)

    def _set_loading_status(self, text: str) -> None:
        if not self._frame_sync.loading.set_status(text):
            return
        self.loading_status_changed.emit(self._frame_sync.loading.status_text())

    def _begin_loading(self, text: str) -> None:
        became_active = self._frame_sync.loading.begin()
        self._reset_held_mouse_actions()
        self._clear_block_break_particles()
        self._set_loading_status(text)
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)
        if bool(became_active):
            self.loading_state_changed.emit(True)
        self.update()

    def _finish_loading(self) -> None:
        if not self._frame_sync.loading.finish():
            return
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)
        self._inp.ensure_mouse_capture_applied()
        self.loading_state_changed.emit(False)
        self.loading_finished.emit()

    def arm_resume_refresh(self) -> None:
        self._frame_sync.arm_resume_refresh()
        self._last_selection_pick_ms = 0.0
        self.update()

    def _invalidate_pause_preview_cache(self) -> None:
        self._pause_preview_cache_key = None
        self._pause_preview_frame = QImage()

    def _clear_pause_preview_frame(self) -> None:
        if self._pause_preview_cache_key is None and self._pause_preview_frame.isNull():
            return
        self._invalidate_pause_preview_cache()
        self._overlay.set_player_preview_frame(QImage())

    def _position_settings_window(self) -> None:
        if self._settings is None:
            return
        if hasattr(self._settings, "prepare_to_show"):
            self._settings.prepare_to_show()
        host = self.window()
        self._settings.adjustSize()
        size = self._settings.size()
        if host is None:
            return
        frame = host.frameGeometry()
        x = int(frame.x() + max(0,(frame.width() - size.width()) // 2))
        y = int(frame.y() + max(0,(frame.height() - size.height()) // 2))
        self._settings.move(int(x), int(y))

    def _position_othello_settings_window(self) -> None:
        if self._othello_settings is None:
            return
        if hasattr(self._othello_settings, "prepare_to_show"):
            self._othello_settings.prepare_to_show()
        host = self.window()
        self._othello_settings.adjustSize()
        size = self._othello_settings.size()
        if host is None:
            return
        frame = host.frameGeometry()
        x = int(frame.x() + max(0,(frame.width() - size.width()) // 2))
        y = int(frame.y() + max(0,(frame.height() - size.height()) // 2))
        self._othello_settings.move(int(x), int(y))

    @staticmethod
    def _pause_preview_key(*, player_state, width: int, height: int, device_pixel_ratio: float) -> tuple[object, ...] | None:
        if player_state is None:
            return None
        return (int(width), int(height), round(float(device_pixel_ratio), 4), round(float(player_state.base_x), 4), round(float(player_state.base_y), 4), round(float(player_state.base_z), 4), round(float(player_state.body_yaw_deg), 4), round(float(player_state.head_yaw_deg), 4), round(float(player_state.head_pitch_deg), 4), round(float(player_state.limb_phase_rad), 4), round(float(player_state.limb_swing_amount), 4), round(float(player_state.crouch_amount), 4), bool(player_state.is_first_person))

    def _build_pause_preview_player_state(self, player_state) -> object:
        body_yaw_deg, head_yaw_deg, head_pitch_deg = self._overlay.player_preview_angles()
        if player_state is None:
            return None
        return replace(player_state, base_x=0.0, base_y=-0.22, base_z=0.0, body_yaw_deg=float(body_yaw_deg), head_yaw_deg=float(head_yaw_deg), head_pitch_deg=float(head_pitch_deg), is_first_person=False)

    def _update_pause_preview_frame(self, player_state, *, fb_w: int, fb_h: int, dpr: float) -> None:
        if not bool(self._overlays.paused()) or bool(self.loading_active()):
            self._clear_pause_preview_frame()
            return
        preview_widget = self._overlay._skin_preview
        if int(preview_widget.width()) <= 1 or int(preview_widget.height()) <= 1:
            self._clear_pause_preview_frame()
            return
        w = max(1, int(round(float(preview_widget.width()) * max(1.0, float(dpr)))))
        h = max(1, int(round(float(preview_widget.height()) * max(1.0, float(dpr)))))
        preview_state = self._build_pause_preview_player_state(player_state)
        preview_key = self._pause_preview_key(player_state=preview_state, width=int(w), height=int(h), device_pixel_ratio=float(dpr))
        if preview_key is not None and self._pause_preview_cache_key == preview_key and not self._pause_preview_frame.isNull():
            self._overlay.set_player_preview_frame(self._pause_preview_frame)
            return
        frame = self._renderer.render_player_preview_frame(w=int(w), h=int(h), player_state=preview_state, restore_framebuffer=int(self.defaultFramebufferObject()), restore_viewport=(0, 0, int(fb_w), int(fb_h)), device_pixel_ratio=float(max(1.0, float(dpr))))
        self._pause_preview_cache_key = preview_key
        self._pause_preview_frame = QImage(frame)
        self._overlay.set_player_preview_frame(frame)

    def _on_application_state_changed(self, state) -> None:
        was_active = bool(self._application_active)
        self._application_active = bool(state == Qt.ApplicationState.ApplicationActive)
        if not bool(self._application_active):
            self._reset_held_mouse_actions()
            self._inp.reset()
            try:
                self._inp.set_mouse_capture(False)
            except Exception:
                pass
            if (not bool(self.loading_active())) and (not self._overlays.dead()):
                interaction_controller.open_pause_menu(self)
        elif not bool(was_active):
            self.arm_resume_refresh()
        settings_controller.sync_cloud_motion_pause(self)
        self._sync_runtime_activity()

    def _sync_runtime_activity(self) -> None:
        self._set_runtime_active(bool(self._gl_initialized) and bool(self.isVisible()) and bool(self._application_active) and (not bool(self._shutdown_done)))

    def _on_frame_swapped(self) -> None:
        self._hud_ctl.on_present_frame()

    def _set_runtime_active(self, active: bool) -> None:
        next_active = bool(active)
        if next_active == bool(self._runtime_active):
            return

        self._runtime_active = bool(next_active)
        if not bool(next_active):
            self._reset_held_mouse_actions()
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
            return

        now = time.perf_counter()
        self._runner.start()
        self._last_paint_ms = 0.0
        self._frame_sync.note_runtime_started(now=float(now))
        self.arm_resume_refresh()
        self._sim_timer.start()
        self._render_timer.start()

    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self._set_runtime_active(False)
        try:
            self._settings.hide()
        except Exception:
            pass
        try:
            self._othello_settings.hide()
        except Exception:
            pass
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
            self._audio.shutdown()
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

    def _effective_render_timer_interval_ms(self) -> int:
        ms = int(self._loop.render_timer_interval_ms)
        if ms > 0:
            return ms
        hz = max(120.0, float(self._loop.sim_hz))
        return max(1, int(round(1000.0 / hz)))

    def set_hud(self, hud) -> None:
        self._hud = hud
        self._hud.setParent(self)
        self._hud.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        self._sync_gameplay_hud_visibility()

    def _invalidate_selection_target(self) -> None:
        self._selection_state.invalidate()
        self._frame_sync.selection.invalidate(force_duration_s=0.12)

    def fullscreen_enabled(self) -> bool:
        return bool(self._state.fullscreen)

    def _make_render_snapshot(self):
        snapshot = self._session.make_snapshot(enable_view_bobbing=bool(self._state.view_bobbing_enabled), enable_camera_shake=bool(self._state.camera_shake_enabled), view_bobbing_strength=float(self._state.view_bobbing_strength), camera_shake_strength=float(self._state.camera_shake_strength), is_first_person_view=bool(self._state.is_first_person_view()))
        return replace(snapshot, block_break_particles=render_samples_from_block_break_particles(self._block_break_particles))

    def _reset_held_mouse_actions(self) -> None:
        self._left_mouse_held = False
        self._right_mouse_held = False
        self._left_mouse_repeat_due_s = 0.0
        self._right_mouse_repeat_due_s = 0.0
        self._right_mouse_repeat_enabled = False

    def _arm_left_mouse_repeat(self, *, now_s: float) -> None:
        self._left_mouse_held = True
        self._left_mouse_repeat_due_s = float(now_s) + float(self._state.block_break_repeat_interval_s)

    def _arm_right_mouse_repeat(self, *, now_s: float) -> None:
        self._right_mouse_held = True
        self._right_mouse_repeat_due_s = float(now_s) + float(self._state.block_place_repeat_interval_s)
        self._right_mouse_repeat_enabled = True

    def _disable_right_mouse_repeat(self) -> None:
        self._right_mouse_repeat_enabled = False

    def _clear_block_break_particles(self) -> None:
        self._block_break_particles = ()

    def _append_block_break_particles(self, particles) -> None:
        if not particles:
            return
        self._block_break_particles = tuple(self._block_break_particles) + tuple(particles)

    def _update_block_break_particles(self, dt: float) -> None:
        self._block_break_particles = advance_block_break_particles(tuple(self._block_break_particles), float(dt))

    def _effective_camera_from_snapshot(self, snapshot) -> tuple[Vec3, float, float, float, Vec3]:
        cam = snapshot.camera
        anchor_eye = Vec3(float(cam.eye_x) + float(cam.shake_tx), float(cam.eye_y) + float(cam.shake_ty), float(cam.eye_z) + float(cam.shake_tz))
        yaw_deg = float(cam.yaw_deg) + float(cam.shake_yaw_deg)
        pitch_deg = float(cam.pitch_deg) + float(cam.shake_pitch_deg)
        roll_deg = float(cam.shake_roll_deg)
        eye, resolved_yaw_deg, resolved_pitch_deg, direction = resolve_camera(world=self._session.world, block_registry=self._session.block_registry, anchor_eye=anchor_eye, yaw_deg=float(yaw_deg), pitch_deg=float(pitch_deg), perspective=str(self._state.camera_perspective))
        return (eye, float(resolved_yaw_deg), float(resolved_pitch_deg), float(roll_deg), direction)

    def _interaction_pose_from_snapshot(self, snapshot) -> tuple[Vec3, float, float, Vec3]:
        cam = snapshot.camera
        eye = Vec3(float(cam.eye_x) + float(cam.shake_tx), float(cam.eye_y) + float(cam.shake_ty), float(cam.eye_z) + float(cam.shake_tz))
        yaw_deg = float(cam.yaw_deg) + float(cam.shake_yaw_deg)
        pitch_deg = float(cam.pitch_deg) + float(cam.shake_pitch_deg)
        direction = forward_from_yaw_pitch_deg(float(yaw_deg), float(pitch_deg))
        return (eye, float(yaw_deg), float(pitch_deg), direction)

    def _gameplay_hud_active(self) -> bool:
        return ((not bool(self.loading_active())) and (not bool(self._state.hide_hud)) and (not self._overlays.dead()) and (not self._overlays.paused()) and (not self._overlays.othello_settings_open()) and (not self._overlays.inventory_open()))

    def _debug_hud_active(self) -> bool:
        return bool(self._state.hud_visible) and bool(self._gameplay_hud_active())

    def _sync_gameplay_hud_visibility(self) -> None:
        show_gameplay_hud = bool(self._gameplay_hud_active())
        show_othello_hud = bool((not bool(self.loading_active())) and (not bool(self._state.hide_hud)) and (not self._overlays.dead()) and (not self._overlays.paused()) and (not self._overlays.inventory_open()) and (not self._overlays.settings_open()) and self._state.is_othello_space() and (not bool(self._state.hud_visible)))
        show_crosshair = bool(show_gameplay_hud and self._state.is_first_person_view())

        self._crosshair.setVisible(bool(show_crosshair))
        self._hotbar.setVisible(bool(show_gameplay_hud))
        self._othello_hud.setVisible(bool(show_othello_hud))

        if self._hud is not None:
            self._hud.setVisible(bool(self._debug_hud_active()))
            if bool(self._debug_hud_active()):
                self._hud.raise_()

        if bool(show_gameplay_hud):
            self._hotbar.raise_()
            if bool(show_crosshair):
                self._crosshair.raise_()
            if self._hud is not None and bool(self._debug_hud_active()):
                self._hud.raise_()
        if bool(show_othello_hud):
            self._othello_hud.raise_()
        self._audio.set_ambient_active(current_space_id=self._state.current_space_id, enabled=bool(show_gameplay_hud))

    def _set_dead_overlay(self, on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
        self._overlays.set_dead(bool(on))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_paused_overlay(self, on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
        self._overlays.set_paused(bool(on))
        self._invalidate_pause_preview_cache()
        if not bool(on):
            self._overlay.set_player_preview_frame(QImage())
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_settings_overlay(self, on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
            self._position_settings_window()
        self._overlays.set_settings_open(bool(on))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_othello_settings_overlay(self, on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
            self._position_othello_settings_window()
        self._overlays.set_othello_settings_open(bool(on))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_inventory_overlay(self, on: bool) -> None:
        if bool(on) and not settings_controller.inventory_available(self):
            return
        if bool(on):
            self._reset_held_mouse_actions()
        self._overlays.set_inventory_open(bool(on))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _arm_world_change_sync(self) -> None:
        self._frame_sync.arm_world_change_sync()

    def _upload_due(self, *, eye: Vec3) -> bool:
        session_token = int(id(self._session))
        world_revision = int(self._session.world.revision)
        render_distance = int(self._state.render_distance_chunks)
        if self._frame_sync.upload.world_revision_changed(world_revision=int(world_revision)):
            self._arm_world_change_sync()
        return self._frame_sync.upload.due(has_ready_results=self._upload.has_ready_results(), visible_chunks_ready=self._upload.visible_chunks_ready(world=self._session.world, eye=eye, render_distance_chunks=int(render_distance)), world_revision=int(world_revision), session_token=int(session_token), render_distance_chunks=int(render_distance), eye=eye)

    def _mark_upload(self, *, eye: Vec3) -> None:
        self._frame_sync.upload.mark(eye=eye, world_revision=int(self._session.world.revision), render_distance_chunks=int(self._state.render_distance_chunks), session_token=int(id(self._session)))

    def _selection_due(self, *, eye: Vec3, yaw_deg: float, pitch_deg: float) -> bool:
        current_space_id = str(self._state.current_space_id)
        current_world_revision = int(self._session.world.revision)

        if self._frame_sync.selection.world_revision_changed(world_revision=int(current_world_revision)):
            self._arm_world_change_sync()
        return self._frame_sync.selection.due(eye=eye, yaw_deg=float(yaw_deg), pitch_deg=float(pitch_deg), current_space_id=str(current_space_id), current_world_revision=int(current_world_revision), target_present=(self._selection_state.target() is not None), is_othello_space=bool(self._state.is_othello_space()))

    def _mark_selection(self, *, eye: Vec3, yaw_deg: float, pitch_deg: float) -> None:
        self._frame_sync.selection.mark(eye=eye, yaw_deg=float(yaw_deg), pitch_deg=float(pitch_deg), current_space_id=str(self._state.current_space_id), current_world_revision=int(self._session.world.revision))

    def initializeGL(self) -> None:
        self._begin_loading("Initializing renderer...")
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

        self._frame_sync.reset_after_gl_initialize()

        self._sync_player_skin_design(push_to_renderer=True, context_current=True)
        settings_controller.apply_runtime_to_renderer(self)
        settings_controller.sync_input_bindings(self)
        settings_controller.sync_audio_preferences(self)
        settings_controller.sync_hotbar_widgets(self)
        settings_controller.sync_crosshair_widgets(self)
        settings_controller.sync_cloud_motion_pause(self)
        othello_controller.sync_hud_text(self)
        self._sync_gameplay_hud_visibility()
        self._gl_initialized = True
        self._begin_loading("Loading world...")
        self._sync_runtime_activity()

    def resizeGL(self, w: int, h: int) -> None:
        if self._hud is not None:
            self._hud.setGeometry(0, 0, max(1, w), max(1, h))

        self._othello_hud.setGeometry(0, 0, max(1, w), max(1, h))
        self._overlay.setGeometry(0, 0, max(1, w), max(1, h))
        self._crosshair.setGeometry(0, 0, max(1, w), max(1, h))
        self._hotbar.setGeometry(0, 0, max(1, w), max(1, h))
        self._inventory.setGeometry(0, 0, max(1, w), max(1, h))
        self._death.setGeometry(0, 0, max(1, w), max(1, h))

        if self._overlays.dead():
            self._death.raise_()
        elif self._overlays.othello_settings_open():
            if self._othello_settings.isVisible():
                self._position_othello_settings_window()
                self._othello_settings.raise_()
        elif self._overlays.settings_open():
            if self._settings.isVisible():
                self._position_settings_window()
                self._settings.raise_()
        elif self._overlays.paused():
            self._overlay.raise_()
        elif self._overlays.inventory_open():
            self._inventory.raise_()
        else:
            self._sync_gameplay_hud_visibility()
            return

        self._sync_gameplay_hud_visibility()

    def paintGL(self) -> None:
        paint_t0 = time.perf_counter()
        self._hud_ctl.on_render_frame()
        self._inp.ensure_mouse_capture_applied()

        snap = self._make_render_snapshot()
        cam = snap.camera
        upload_eye = Vec3(float(cam.eye_x), float(cam.eye_y), float(cam.eye_z))
        render_eye, render_yaw_deg, render_pitch_deg, render_roll_deg, _render_direction = (self._effective_camera_from_snapshot(snap))
        interaction_eye, interaction_yaw_deg, interaction_pitch_deg, _interaction_direction = self._interaction_pose_from_snapshot(snap)
        self._audio.cache_listener_pose(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg))

        if self._upload_due(eye=upload_eye):
            self._upload.upload_if_needed(world=self._session.world, renderer=self._renderer, eye=upload_eye, render_distance_chunks=int(self._state.render_distance_chunks))
            self._mark_upload(eye=upload_eye)

        if bool(self.loading_active()):
            ready_chunks, total_chunks = self._upload.visible_load_progress(world=self._session.world, eye=upload_eye, render_distance_chunks=int(self._state.render_distance_chunks))
            if self._frame_sync.loading.set_progress(ready_chunks=int(ready_chunks), total_chunks=int(total_chunks)):
                if int(total_chunks) > 0:
                    self._set_loading_status(f"Loading world... {int(ready_chunks)}/{int(total_chunks)} chunks")
                else:
                    self._set_loading_status("Loading world...")
            if self._upload.visible_chunks_ready(world=self._session.world, eye=upload_eye, render_distance_chunks=int(self._state.render_distance_chunks)):
                self._finish_loading()

        if not bool(self.loading_active()):
            if self._state.is_othello_space():
                if self._selection_due(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg)):
                    self._last_selection_pick_ms = 0.0
                    self._invalidate_selection_target()
                    self._renderer.clear_selection()
                    othello_controller.refresh_hover_square(self, snap)
                    self._mark_selection(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg))
            else:
                self._othello_hover_square = None
                if self._selection_due(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg)):
                    self._last_selection_pick_ms = self._selection_state.refresh(session=self._session, reach=float(self._state.reach), eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg))
                    selection_target = self._selection_state.target()
                    if selection_target is None:
                        self._renderer.clear_selection()
                    else:
                        hx, hy, hz, st = selection_target

                        def get_state(x: int, y: int, z: int) -> str | None:
                            return self._session.world.blocks.get((int(x), int(y), int(z)))

                        self._renderer.set_selection_target(x=int(hx), y=int(hy), z=int(hz), state_str=str(st), get_state=get_state, world_revision=int(self._session.world.revision))
                    self._mark_selection(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg))

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        player_state = compose_player_render_state(snapshot=snap, motion=self._first_person_motion.sample(), block_registry=self._session.block_registry)

        self._renderer.render(w=fb_w, h=fb_h, eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg), fov_deg=float(cam.fov_deg), render_distance_chunks=int(self._state.render_distance_chunks), player_state=player_state, othello_state=othello_controller.build_render_state(self), falling_blocks=tuple(snap.falling_blocks), block_break_particles=tuple(snap.block_break_particles))
        self._update_pause_preview_frame(player_state, fb_w=int(fb_w), fb_h=int(fb_h), dpr=float(dpr))
        self._last_paint_ms = float((time.perf_counter() - paint_t0) * 1000.0)

    def _tick_sim(self) -> None:
        if bool(self.loading_active()) or (self._overlays.dead() or self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open()):
            return
        self._runner.update()

    def _on_step(self, dt: float) -> None:
        othello_controller.consume_pending_ai_result(self)
        self._update_block_break_particles(float(dt))

        self._inp.poll_relative_mouse_delta()
        fr, md = self._inp.consume(invert_x=self._state.invert_x, invert_y=self._state.invert_y)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        sprint = bool(fr.sprint)
        if bool(self._state.auto_sprint_enabled) and float(fr.move_f) > 1e-6 and (not bool(fr.crouch)):
            sprint = True

        step_result = self._session.step(dt=float(dt), move_f=fr.move_f, move_s=fr.move_s, jump_held=bool(fr.jump_held), jump_pressed=bool(fr.jump_pressed), sprint=bool(sprint), crouch=bool(fr.crouch), mdx=float(md.dx), mdy=float(md.dy), creative_mode=bool(self._state.creative_mode), auto_jump_enabled=bool(self._state.auto_jump_enabled))
        settings_controller.sync_first_person_target(self)
        self._first_person_motion.update(float(dt))
        self._hud_ctl.on_sim_step(dt=float(dt), player=self._session.player, jump_started=bool(step_result.jump_started))

        if bool(step_result.footstep_triggered):
            self._audio.play_surface_event(event_name=PLAYER_EVENT_STEP, support_block_state=step_result.support_block_state, position=step_result.support_position)

        if bool(step_result.landed):
            self._audio.play_surface_event(event_name=PLAYER_EVENT_LAND, support_block_state=step_result.support_block_state, position=step_result.support_position, fall_distance_blocks=float(step_result.fall_distance_blocks))

        if self._state.is_othello_space():
            state_before = self._othello_match.game_state()
            state_after = self._othello_match.tick(float(dt), paused=False)
            significant_othello_change = bool(state_before.status != state_after.status or state_before.board != state_after.board or state_before.current_turn != state_after.current_turn or state_before.legal_moves != state_after.legal_moves or state_before.thinking != state_after.thinking or state_before.last_move_index != state_after.last_move_index or state_before.animations != state_after.animations or state_before.message != state_after.message or state_before.winner != state_after.winner)
            if bool(significant_othello_change):
                othello_controller.sync_hud_text(self)
                othello_controller.maybe_request_ai(self)
                othello_controller.maybe_request_analysis(self)
            else:
                now = time.perf_counter()
                if (float(now) - float(self._othello_last_passive_hud_sync_s)) >= 0.20:
                    self._othello_last_passive_hud_sync_s = float(now)
                    othello_controller.sync_hud_text(self)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        interaction_controller.handle_held_mouse_buttons(self)

        if not self._hud_ctl.should_emit() or not bool(self._debug_hud_active()):
            return

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        payload = self._hud_ctl.build_payload(session=self._session, renderer=self._renderer, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, creative_mode=self._state.creative_mode, flying=bool(self._session.player.flying), inventory_open=self._overlays.inventory_open(), selected_block_id=settings_controller.current_item_id(self) or "", reach=self._state.reach, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, shadow_enabled=self._state.shadow_enabled, world_wire=self._state.world_wire, cloud_wire=self._state.cloud_wire, cloud_enabled=self._state.cloud_enabled, cloud_density=self._state.cloud_density, cloud_seed=self._state.cloud_seed, debug_shadow=self._state.debug_shadow, fb_w=fb_w, fb_h=fb_h, dpr=dpr, vsync_on=self._state.vsync_on, render_timer_interval_ms=int(self._render_timer.interval()), sim_hz=float(self._loop.sim_hz), render_distance_chunks=int(self._state.render_distance_chunks), paint_ms=float(self._last_paint_ms), selection_pick_ms=float(self._last_selection_pick_ms))
        self.hud_updated.emit(payload)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        if interaction_controller.handle_key_press(self, e):
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        if interaction_controller.handle_wheel(self, e):
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        interaction_controller.handle_mouse_press(self, e)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        interaction_controller.handle_mouse_release(self, e)
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if bool(self.loading_active()) or (self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open() or (not self._inp.captured())):
            super().mouseMoveEvent(e)
            return
        e.accept()
        return

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self.arm_resume_refresh()
        settings_controller.sync_cloud_motion_pause(self)
        self._sync_runtime_activity()

    def hideEvent(self, e) -> None:
        self._set_runtime_active(False)
        settings_controller.sync_cloud_motion_pause(self)
        super().hideEvent(e)
