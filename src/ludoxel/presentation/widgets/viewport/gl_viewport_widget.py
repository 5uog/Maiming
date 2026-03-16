# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/viewport/gl_viewport_widget.py
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
from ....infrastructure.platform.qt_input_adapter import QtInputAdapter
from ....infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from ...config.game_loop_params import DEFAULT_GAME_LOOP_PARAMS, GameLoopParams
from ...config.gl_surface_format import build_gl_surface_format
from ...hud.hud_controller import HudController
from ..hud.crosshair_widget import CrosshairWidget
from ..hud.hotbar_widget import HotbarWidget
from ..overlays.death_overlay import DeathOverlay
from ..overlays.inventory_overlay import InventoryOverlay
from ..overlays.pause_overlay import PauseOverlay
from ..othello.ai_worker import OthelloAiWorker
from ..othello.hud_widget import OthelloHudWidget
from ..othello.settings_overlay import OthelloSettingsOverlay
from ..settings.overlay import SettingsOverlay
from .first_person_motion import FirstPersonMotionController
from . import viewport_event_handlers, viewport_othello_controller, viewport_settings_controller
from .viewport_input import ViewportInput
from .viewport_overlays import OverlayRefs, ViewportOverlays
from ....application.session.runtime_persistence import apply_persisted_state_if_present, save_state
from ....application.session.runtime_preferences import ViewportRuntimeState
from .viewport_selection_state import ViewportSelectionState
from .viewport_world_upload import WorldUploadTracker
from .player_render_state_composer import compose_player_render_state


class GLViewportWidget(QOpenGLWidget):
    hud_updated = pyqtSignal(object)
    fullscreen_changed = pyqtSignal(bool)

    def __init__(self, project_root: Path, parent=None, loop_params: GameLoopParams=DEFAULT_GAME_LOOP_PARAMS) -> None:
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
        viewport_settings_controller.sync_state_from_renderer_sun(self)
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

        self._last_paint_ms: float = 0.0
        self._last_selection_pick_ms: float = 0.0
        self._shutdown_done = False

        self._overlay = PauseOverlay(self)

        self._settings = SettingsOverlay(self)

        self._othello_settings = OthelloSettingsOverlay(self)

        self._death = DeathOverlay(self)

        self._crosshair = CrosshairWidget(self)
        self._crosshair.setVisible(True)

        self._hotbar = HotbarWidget(parent=self, project_root=self._project_root, registry=self._session.block_registry)
        self._hotbar.setVisible(True)

        self._inventory = InventoryOverlay(parent=self, project_root=self._project_root, registry=self._session.block_registry)

        self._overlays = ViewportOverlays(refs=OverlayRefs(pause=self._overlay, settings=self._settings, othello_settings=self._othello_settings, inventory=self._inventory, death=self._death, crosshair=self._crosshair, hotbar=self._hotbar, hud_getter=lambda: self._hud, othello_hud_getter=lambda: self._othello_hud), runner=self._runner, inp=self._inp)
        viewport_settings_controller.bind_settings_overlay(self)
        viewport_othello_controller.bind_othello_controls(self)
        viewport_event_handlers.bind_overlay_actions(self)

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

        viewport_settings_controller.apply_runtime_to_renderer(self)
        viewport_settings_controller.sync_hotbar_widgets(self)
        viewport_settings_controller.sync_first_person_target(self)
        viewport_settings_controller.sync_view_model_visibility(self)
        viewport_othello_controller.sync_hud_text(self)
        self._sync_gameplay_hud_visibility()

    def _for_each_session(self, fn) -> None:
        for session in self._sessions.all_sessions():
            fn(session)

    def save_state(self) -> None:
        viewport_settings_controller.sync_state_from_renderer_sun(self)
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
        if bool(on) and not viewport_settings_controller.inventory_available(self):
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

        viewport_settings_controller.apply_runtime_to_renderer(self)
        viewport_settings_controller.sync_hotbar_widgets(self)
        viewport_settings_controller.sync_cloud_motion_pause(self)
        viewport_othello_controller.sync_hud_text(self)
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
            viewport_othello_controller.refresh_hover_square(self, snap)
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
        player_state = compose_player_render_state(snapshot=snap, motion=self._first_person_motion.sample(), block_registry=self._session.block_registry)

        self._renderer.render(w=fb_w, h=fb_h, eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg), fov_deg=float(cam.fov_deg), render_distance_chunks=int(self._state.render_distance_chunks), player_state=player_state, othello_state=viewport_othello_controller.build_render_state(self))
        self._last_paint_ms = float((time.perf_counter() - paint_t0) * 1000.0)

    def _tick_sim(self) -> None:
        if self._overlays.dead() or self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open():
            return
        self._runner.update()

    def _on_step(self, dt: float) -> None:
        viewport_othello_controller.consume_pending_ai_result(self)

        self._inp.poll_relative_mouse_delta()
        fr, md = self._inp.consume(invert_x=self._state.invert_x, invert_y=self._state.invert_y)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        sprint = bool(fr.sprint)
        if bool(self._state.auto_sprint_enabled) and float(fr.move_f) > 1e-6 and (not bool(fr.crouch)):
            sprint = True

        jump_started = self._session.step(dt=float(dt), move_f=fr.move_f, move_s=fr.move_s, jump_held=bool(fr.jump_held), jump_pressed=bool(fr.jump_pressed), sprint=bool(sprint), crouch=bool(fr.crouch), mdx=float(md.dx), mdy=float(md.dy), creative_mode=bool(self._state.creative_mode), auto_jump_enabled=bool(self._state.auto_jump_enabled))
        viewport_settings_controller.sync_first_person_target(self)
        self._first_person_motion.update(float(dt))
        self._hud_ctl.on_sim_step(dt=float(dt), player=self._session.player, jump_started=bool(jump_started))

        if self._state.is_othello_space():
            self._othello_match.tick(float(dt), paused=False)
            viewport_othello_controller.sync_hud_text(self)
            viewport_othello_controller.maybe_request_ai(self)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        if not self._hud_ctl.should_emit() or not bool(self._debug_hud_active()):
            return

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        payload = self._hud_ctl.build_payload(session=self._session, renderer=self._renderer, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, creative_mode=self._state.creative_mode, flying=bool(self._session.player.flying), inventory_open=self._overlays.inventory_open(), selected_block_id=viewport_settings_controller.current_item_id(self) or "", reach=self._state.reach, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, shadow_enabled=self._state.shadow_enabled, world_wire=self._state.world_wire, cloud_wire=self._state.cloud_wire, cloud_enabled=self._state.cloud_enabled, cloud_density=self._state.cloud_density, cloud_seed=self._state.cloud_seed, debug_shadow=self._state.debug_shadow, fb_w=fb_w, fb_h=fb_h, dpr=dpr, vsync_on=self._state.vsync_on, render_timer_interval_ms=int(self._render_timer.interval()), sim_hz=float(self._loop.sim_hz), render_distance_chunks=int(self._state.render_distance_chunks), paint_ms=float(self._last_paint_ms), selection_pick_ms=float(self._last_selection_pick_ms))
        self.hud_updated.emit(payload)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if viewport_event_handlers.handle_key_press(self, e):
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if viewport_event_handlers.handle_wheel(self, e):
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        viewport_event_handlers.handle_mouse_press(self, e)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open() or (not self._inp.captured()):
            super().mouseMoveEvent(e)
            return
        e.accept()
        return
