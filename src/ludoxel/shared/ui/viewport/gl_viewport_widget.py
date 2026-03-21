# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QMessageBox

from ....application.runtime.context.play_space_context import PlaySpaceContext
from ....application.runtime.state.runtime_preferences import RuntimePreferences
from ....features.othello.application.othello_match_controller import OthelloMatchController
from ....application.runtime.tasks.fixed_step_runner import FixedStepRunner
from ....application.runtime.tasks.state_persistence import apply_persisted_state_if_present, save_state
from ...math.vec3 import Vec3
from ...math.view_angles import forward_from_yaw_pitch_deg
from ....application.audio import AudioManager, PLAYER_EVENT_LAND, PLAYER_EVENT_STEP
from ..qt_input_adapter import QtInputAdapter
from ...opengl.runtime.gl_renderer import GLRenderer
from ..config.game_loop_params import DEFAULT_GAME_LOOP_PARAMS, GameLoopParams
from ..config.gl_surface_format import build_gl_surface_format
from ..hud.hud_controller import HudController
from ..hud.crosshair_widget import CrosshairWidget
from ..hud.hotbar_widget import HotbarWidget
from ....features.othello.domain.game.ai_worker import OthelloAiWorker
from ....features.othello.ui.hud_widget import OthelloHudWidget
from ....features.othello.ui.settings_overlay import OthelloSettingsOverlay
from ..overlays.death_overlay import DeathOverlay
from ..overlays.inventory_overlay import InventoryOverlay
from ..overlays.pause_overlay import PauseOverlay
from ..settings.overlay import SettingsOverlay
from .controllers import interaction_controller, settings_controller
from ....features.othello.ui.viewport import othello_controller as othello_controller
from ...rendering.first_person_motion import FirstPersonMotionController
from ...rendering.player_render_state_composer import compose_player_render_state
from .runtime.input_controller import ViewportInput
from .runtime.overlay_controller import OverlayRefs, ViewportOverlays
from .runtime.selection_state import ViewportSelectionState
from ...opengl.runtime.world_upload_tracker import WorldUploadTracker

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

        self._last_paint_ms: float = 0.0
        self._last_selection_pick_ms: float = 0.0
        self._shutdown_done = False

        self._last_upload_eye: Vec3 | None = None
        self._last_upload_world_revision: int = -1
        self._last_upload_render_distance_chunks: int = -1
        self._last_upload_session_token: int = -1
        self._last_upload_time_s: float = 0.0
        self._upload_interval_s: float = 1.0 / 20.0
        self._upload_linear_threshold_sq: float = 1.0 * 1.0
        self._force_upload_until_s: float = 0.0

        self._last_selection_pose: tuple[float, float, float, float, float] | None = None
        self._last_selection_space_id: str = ""
        self._last_selection_world_revision: int = -1
        self._last_selection_refresh_time_s: float = 0.0
        self._selection_refresh_interval_s: float = 1.0 / 30.0
        self._selection_linear_threshold_sq: float = 0.20 * 0.20
        self._selection_angular_threshold_deg: float = 0.75
        self._force_selection_until_s: float = 0.0

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
        settings_controller.bind_settings_overlay(self)
        othello_controller.bind_othello_controls(self)
        interaction_controller.bind_overlay_actions(self)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._sim_timer = QTimer(self)
        self._sim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._sim_timer.setInterval(int(self._effective_sim_timer_interval_ms()))
        self._sim_timer.timeout.connect(self._tick_sim)

        self._render_timer = QTimer(self)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._render_timer.setInterval(int(self._effective_render_timer_interval_ms()))
        self._render_timer.timeout.connect(self.update)

        self.setFormat(build_gl_surface_format())

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
        settings_controller.sync_first_person_target(self)
        settings_controller.sync_view_model_visibility(self)
        othello_controller.sync_hud_text(self)
        self._sync_gameplay_hud_visibility()

    def _for_each_session(self, fn) -> None:
        for session in self._sessions.all_sessions():
            fn(session)

    def save_state(self) -> None:
        settings_controller.sync_state_from_renderer_sun(self)
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
        return 16

    def set_hud(self, hud) -> None:
        self._hud = hud
        self._hud.setParent(self)
        self._hud.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        self._sync_gameplay_hud_visibility()

    def _invalidate_selection_target(self) -> None:
        self._selection_state.invalidate()
        self._last_selection_pose = None
        self._last_selection_space_id = ""
        self._last_selection_world_revision = -1
        self._force_selection_until_s = time.perf_counter() + 0.12

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
        self._audio.set_ambient_active(current_space_id=self._state.current_space_id, enabled=bool(show_gameplay_hud))

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
        if bool(on) and not settings_controller.inventory_available(self):
            return
        self._overlays.set_inventory_open(bool(on))
        self._sync_gameplay_hud_visibility()

    @staticmethod
    def _angle_delta_deg(left: float, right: float) -> float:
        delta = (float(left) - float(right) + 180.0) % 360.0 - 180.0
        return abs(float(delta))

    def _arm_world_change_sync(self) -> None:
        now = time.perf_counter()
        self._force_upload_until_s = max(float(self._force_upload_until_s), now + 0.12)
        self._force_selection_until_s = max(float(self._force_selection_until_s), now + 0.12)

    def _upload_due(self, *, eye: Vec3) -> bool:
        session_token = int(id(self._session))
        world_revision = int(self._session.world.revision)
        render_distance = int(self._state.render_distance_chunks)
        now = time.perf_counter()

        if world_revision != int(self._last_upload_world_revision):
            self._arm_world_change_sync()
            return True
        if now < float(self._force_upload_until_s):
            return True
        if session_token != int(self._last_upload_session_token):
            return True
        if render_distance != int(self._last_upload_render_distance_chunks):
            return True
        if self._last_upload_eye is None:
            return True

        dx = float(eye.x) - float(self._last_upload_eye.x)
        dy = float(eye.y) - float(self._last_upload_eye.y)
        dz = float(eye.z) - float(self._last_upload_eye.z)
        moved_sq = (dx * dx) + (dy * dy) + (dz * dz)

        if moved_sq < float(self._upload_linear_threshold_sq):
            return False

        return (now - float(self._last_upload_time_s)) >= float(self._upload_interval_s)

    def _mark_upload(self, *, eye: Vec3) -> None:
        self._last_upload_eye = Vec3(float(eye.x), float(eye.y), float(eye.z))
        self._last_upload_world_revision = int(self._session.world.revision)
        self._last_upload_render_distance_chunks = int(self._state.render_distance_chunks)
        self._last_upload_session_token = int(id(self._session))
        self._last_upload_time_s = time.perf_counter()

    def _selection_due(self, *, eye: Vec3, yaw_deg: float, pitch_deg: float) -> bool:
        now = time.perf_counter()
        current_space_id = str(self._state.current_space_id)
        current_world_revision = int(self._session.world.revision)

        if current_world_revision != int(self._last_selection_world_revision):
            self._arm_world_change_sync()
            return True
        if now < float(self._force_selection_until_s):
            return True
        if current_space_id != str(self._last_selection_space_id):
            return True
        if self._last_selection_pose is None:
            return True
        if not self._state.is_othello_space() and self._selection_state.target() is None:
            return True
        if (now - float(self._last_selection_refresh_time_s)) >= float(self._selection_refresh_interval_s):
            px, py, pz, pyaw, ppitch = self._last_selection_pose
            dx = float(eye.x) - float(px)
            dy = float(eye.y) - float(py)
            dz = float(eye.z) - float(pz)
            moved_sq = (dx * dx) + (dy * dy) + (dz * dz)
            yaw_delta = self._angle_delta_deg(float(yaw_deg), float(pyaw))
            pitch_delta = self._angle_delta_deg(float(pitch_deg), float(ppitch))
            if moved_sq >= float(self._selection_linear_threshold_sq):
                return True
            if yaw_delta >= float(self._selection_angular_threshold_deg):
                return True
            if pitch_delta >= float(self._selection_angular_threshold_deg):
                return True
        return False

    def _mark_selection(self, *, eye: Vec3, yaw_deg: float, pitch_deg: float) -> None:
        self._last_selection_pose = (float(eye.x), float(eye.y), float(eye.z), float(yaw_deg), float(pitch_deg))
        self._last_selection_space_id = str(self._state.current_space_id)
        self._last_selection_world_revision = int(self._session.world.revision)
        self._last_selection_refresh_time_s = time.perf_counter()

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

        self._last_upload_eye = None
        self._last_upload_world_revision = -1
        self._last_upload_render_distance_chunks = -1
        self._last_upload_session_token = -1
        self._last_upload_time_s = 0.0
        self._force_upload_until_s = time.perf_counter() + 0.12

        self._last_selection_pose = None
        self._last_selection_space_id = ""
        self._last_selection_world_revision = -1
        self._last_selection_refresh_time_s = 0.0
        self._force_selection_until_s = time.perf_counter() + 0.12

        settings_controller.apply_runtime_to_renderer(self)
        settings_controller.sync_input_bindings(self)
        settings_controller.sync_audio_preferences(self)
        settings_controller.sync_hotbar_widgets(self)
        settings_controller.sync_cloud_motion_pause(self)
        othello_controller.sync_hud_text(self)
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
        render_eye, render_yaw_deg, render_pitch_deg, render_roll_deg, _render_direction = (self._effective_camera_from_snapshot(snap))
        self._audio.cache_listener_pose(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg))

        if self._upload_due(eye=eye):
            self._upload.upload_if_needed(world=self._session.world, renderer=self._renderer, eye=eye, render_distance_chunks=int(self._state.render_distance_chunks))
            self._mark_upload(eye=eye)

        if self._state.is_othello_space():
            if self._selection_due(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg)):
                self._last_selection_pick_ms = 0.0
                self._invalidate_selection_target()
                self._renderer.clear_selection()
                othello_controller.refresh_hover_square(self, snap)
                self._mark_selection(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg))
        else:
            self._othello_hover_square = None
            if self._selection_due(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg)):
                self._last_selection_pick_ms = self._selection_state.refresh(session=self._session, reach=float(self._state.reach), eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg))
                selection_target = self._selection_state.target()
                if selection_target is None:
                    self._renderer.clear_selection()
                else:
                    hx, hy, hz, st = selection_target

                    def get_state(x: int, y: int, z: int) -> str | None:
                        return self._session.world.blocks.get((int(x), int(y), int(z)))

                    self._renderer.set_selection_target(x=int(hx), y=int(hy), z=int(hz), state_str=str(st), get_state=get_state, world_revision=int(self._session.world.revision))
                self._mark_selection(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg))

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        cam = snap.camera
        player_state = compose_player_render_state(snapshot=snap, motion=self._first_person_motion.sample(), block_registry=self._session.block_registry)

        self._renderer.render(w=fb_w, h=fb_h, eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg), fov_deg=float(cam.fov_deg), render_distance_chunks=int(self._state.render_distance_chunks), player_state=player_state, othello_state=othello_controller.build_render_state(self))
        self._last_paint_ms = float((time.perf_counter() - paint_t0) * 1000.0)

    def _tick_sim(self) -> None:
        if (self._overlays.dead() or self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open()):
            return
        self._runner.update()

    def _on_step(self, dt: float) -> None:
        othello_controller.consume_pending_ai_result(self)

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
            self._othello_match.tick(float(dt), paused=False)
            othello_controller.sync_hud_text(self)
            othello_controller.maybe_request_ai(self)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        if not self._hud_ctl.should_emit() or not bool(self._debug_hud_active()):
            return

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        payload = self._hud_ctl.build_payload(session=self._session, renderer=self._renderer, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, creative_mode=self._state.creative_mode, flying=bool(self._session.player.flying), inventory_open=self._overlays.inventory_open(), selected_block_id=settings_controller.current_item_id(self) or "", reach=self._state.reach, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, shadow_enabled=self._state.shadow_enabled, world_wire=self._state.world_wire, cloud_wire=self._state.cloud_wire, cloud_enabled=self._state.cloud_enabled, cloud_density=self._state.cloud_density, cloud_seed=self._state.cloud_seed, debug_shadow=self._state.debug_shadow, fb_w=fb_w, fb_h=fb_h, dpr=dpr, vsync_on=self._state.vsync_on, render_timer_interval_ms=int(self._render_timer.interval()), sim_hz=float(self._loop.sim_hz), render_distance_chunks=int(self._state.render_distance_chunks), paint_ms=float(self._last_paint_ms), selection_pick_ms=float(self._last_selection_pick_ms))
        self.hud_updated.emit(payload)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if interaction_controller.handle_key_press(self, e):
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if interaction_controller.handle_wheel(self, e):
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        interaction_controller.handle_mouse_press(self, e)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if (self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open() or (not self._inp.captured())):
            super().mouseMoveEvent(e)
            return
        e.accept()
        return
