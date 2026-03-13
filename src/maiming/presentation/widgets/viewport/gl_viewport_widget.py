# FILE: src/maiming/presentation/widgets/viewport/gl_viewport_widget.py
from __future__ import annotations
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent
from PyQt6.QtWidgets import QMessageBox

from ....core.math.vec3 import Vec3
from ....application.session.fixed_step_runner import FixedStepRunner
from ....application.session.session_manager import SessionManager
from ....infrastructure.platform.qt_input_adapter import QtInputAdapter
from ....infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from ....infrastructure.rendering.opengl.facade.player_render_state import FirstPersonRenderState, PlayerRenderState

from ...config.game_loop_params import GameLoopParams, DEFAULT_GAME_LOOP_PARAMS
from ...config.gl_surface_format import build_gl_surface_format
from ...hud.hud_controller import HudController
from ..common import hotbar_index_from_key
from ..hud.crosshair_widget import CrosshairWidget
from ..hud.hotbar_widget import HotbarWidget
from ..overlays.death_overlay import DeathOverlay
from ..overlays.inventory_overlay import InventoryOverlay
from ..overlays.pause_overlay import PauseOverlay
from ..overlays.settings_overlay import SettingsOverlay
from .viewport_input import ViewportInput
from .viewport_overlays import ViewportOverlays, OverlayRefs
from .viewport_persistence import apply_persisted_state_if_present, save_state
from .first_person_motion import FirstPersonMotionController
from .viewport_runtime_state import ViewportRuntimeState
from .viewport_selection_state import ViewportSelectionState
from .viewport_world_upload import WorldUploadTracker

class GLViewportWidget(QOpenGLWidget):
    hud_updated = pyqtSignal(object)

    def __init__(self, project_root: Path, parent=None, loop_params: GameLoopParams = DEFAULT_GAME_LOOP_PARAMS) -> None:
        super().__init__(parent)

        self._project_root = Path(project_root)
        self._assets_dir = self._project_root / "assets"
        self._loop = loop_params

        self._adapter = QtInputAdapter(self)
        self._inp = ViewportInput(widget=self, adapter=self._adapter)

        self._session = SessionManager.create_default(seed=0)
        self._runner = FixedStepRunner(step_dt=self._loop.step_dt(), on_step=self._on_step)

        self._renderer = GLRenderer()
        self._hud = None

        self._upload = WorldUploadTracker()
        self._hud_ctl = HudController()

        self._state = ViewportRuntimeState()
        self._sync_state_from_renderer_sun()
        self._first_person_motion = FirstPersonMotionController(slim_arm=True)

        self._selection_state = ViewportSelectionState()

        self._last_paint_ms: float = 0.0
        self._last_selection_pick_ms: float = 0.0

        self._shutdown_done = False

        self._overlay = PauseOverlay(self)
        self._overlay.resume_requested.connect(self._resume_from_overlay)
        self._overlay.settings_requested.connect(self._open_settings_from_pause)

        self._settings = SettingsOverlay(self)
        self._settings.back_requested.connect(self._back_from_settings)
        self._settings.fov_changed.connect(self._set_fov)
        self._settings.sens_changed.connect(self._set_sens)
        self._settings.invert_x_changed.connect(self._set_invert_x)
        self._settings.invert_y_changed.connect(self._set_invert_y)
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

        self._overlays = ViewportOverlays(refs=OverlayRefs(pause=self._overlay, settings=self._settings, inventory=self._inventory, death=self._death, crosshair=self._crosshair, hotbar=self._hotbar, hud_getter=lambda: self._hud), runner=self._runner, inp=self._inp)

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

        self._state = apply_persisted_state_if_present(project_root=self._project_root, session=self._session, renderer=self._renderer)
        self._apply_runtime_to_renderer()
        self._sync_hotbar_widgets()
        self._first_person_motion.prime(self._current_block_id())

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

    def _sync_hotbar_widgets(self) -> None:
        self._state.normalize()
        slots = self._state.hotbar_snapshot()
        idx = int(self._state.creative_selected_hotbar_index if bool(self._state.creative_mode) else self._state.survival_selected_hotbar_index)
        self._inventory.set_creative_mode(bool(self._state.creative_mode))
        self._inventory.sync_hotbar(slots=slots, selected_index=idx)
        self._hotbar.sync_hotbar(slots=slots, selected_index=idx)

    def _current_block_id(self) -> str | None:
        self._state.normalize()
        return self._state.current_block_id()

    def _sync_first_person_target(self) -> None:
        self._first_person_motion.set_target_block_id(self._current_block_id())

    def _select_hotbar_slot(self, slot_index: int) -> None:
        self._state.select_hotbar_index(int(slot_index))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _assign_hotbar_slot(self, slot_index: int, block_id: str) -> None:
        self._state.set_hotbar_slot(int(slot_index), str(block_id))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _cycle_hotbar(self, step: int) -> None:
        self._state.cycle_hotbar(int(step))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def save_state(self) -> None:
        self._sync_state_from_renderer_sun()
        save_state(project_root=self._project_root, session=self._session, renderer=self._renderer, runtime=self._state)

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
        self._hud.setVisible(bool(self._state.hud_visible))
        if bool(self._state.hud_visible):
            self._hud.show()
            self._hotbar.raise_()
            self._crosshair.raise_()
            self._hud.raise_()

    def _invalidate_selection_target(self) -> None:
        self._selection_state.invalidate()

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

        self._runner.start()
        self._sim_timer.start()
        self._render_timer.start()

    def resizeGL(self, w: int, h: int) -> None:
        if self._hud is not None:
            self._hud.setGeometry(0, 0, max(1, w), max(1, h))
            if bool(self._state.hud_visible):
                self._hud.raise_()

        self._overlay.setGeometry(0, 0, max(1, w), max(1, h))
        self._settings.setGeometry(0, 0, max(1, w), max(1, h))
        self._crosshair.setGeometry(0, 0, max(1, w), max(1, h))
        self._hotbar.setGeometry(0, 0, max(1, w), max(1, h))
        self._inventory.setGeometry(0, 0, max(1, w), max(1, h))
        self._death.setGeometry(0, 0, max(1, w), max(1, h))

        if self._overlays.dead():
            self._death.raise_()
        elif self._overlays.settings_open():
            self._settings.raise_()
        elif self._overlays.paused():
            self._overlay.raise_()
        elif self._overlays.inventory_open():
            self._inventory.raise_()
        else:
            self._hotbar.raise_()
            self._crosshair.raise_()

    def paintGL(self) -> None:
        paint_t0 = time.perf_counter()
        self._hud_ctl.on_render_frame()

        snap = self._session.make_snapshot()
        eye = Vec3(snap.camera.eye_x, snap.camera.eye_y, snap.camera.eye_z)

        self._upload.upload_if_needed(world=self._session.world, renderer=self._renderer, eye=eye, render_distance_chunks=int(self._state.render_distance_chunks))

        self._last_selection_pick_ms = self._selection_state.refresh(session=self._session, reach=float(self._state.reach))

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
        first_person = FirstPersonRenderState(visible_block_id=motion.visible_block_id, visible_block_kind=None if visible_def is None else str(visible_def.kind), target_block_id=motion.target_block_id, equip_progress=float(motion.equip_progress), prev_equip_progress=float(motion.prev_equip_progress), swing_progress=float(motion.swing_progress), prev_swing_progress=float(motion.prev_swing_progress), show_arm=bool(motion.show_arm), slim_arm=bool(motion.slim_arm))
        player_state = PlayerRenderState(base_x=float(pl.base_x), base_y=float(pl.base_y), base_z=float(pl.base_z), body_yaw_deg=float(pl.body_yaw_deg), head_yaw_deg=float(pl.head_yaw_deg), head_pitch_deg=float(pl.head_pitch_deg), limb_phase_rad=float(pl.limb_phase_rad), limb_swing_amount=float(pl.limb_swing_amount), crouch_amount=float(pl.crouch_amount), is_first_person=bool(pl.is_first_person), first_person=first_person)

        self._renderer.render(w=fb_w, h=fb_h, eye=Vec3(cam.eye_x, cam.eye_y, cam.eye_z), yaw_deg=cam.yaw_deg, pitch_deg=cam.pitch_deg, fov_deg=cam.fov_deg, render_distance_chunks=int(self._state.render_distance_chunks), player_state=player_state)
        self._last_paint_ms = float((time.perf_counter() - paint_t0) * 1000.0)

    def _tick_sim(self) -> None:
        if self._overlays.dead():
            return
        if self._overlays.paused():
            return
        if self._overlays.settings_open():
            return
        self._runner.update()

    def _sync_settings_values(self) -> None:
        self._sync_state_from_renderer_sun()

        self._settings.sync_values(fov_deg=self._session.settings.fov_deg, sens_deg_per_px=self._session.settings.mouse_sens_deg_per_px, inv_x=self._state.invert_x, inv_y=self._state.invert_y, outline_selection=self._state.outline_selection, cloud_wire=self._state.cloud_wire, clouds_enabled=self._state.cloud_enabled, cloud_density=int(self._state.cloud_density), cloud_seed=int(self._state.cloud_seed), cloud_flow_direction=str(self._state.cloud_flow_direction), world_wire=self._state.world_wire, shadow_enabled=self._state.shadow_enabled, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, creative_mode=self._state.creative_mode, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, gravity=float(self._session.settings.movement.gravity), walk_speed=float(self._session.settings.movement.walk_speed), sprint_speed=float(self._session.settings.movement.sprint_speed), jump_v0=float(self._session.settings.movement.jump_v0), auto_jump_cooldown_s=float(self._session.settings.movement.auto_jump_cooldown_s), fly_speed=float(self._session.settings.movement.fly_speed), fly_ascend_speed=float(self._session.settings.movement.fly_ascend_speed), fly_descend_speed=float(self._session.settings.movement.fly_descend_speed), render_distance_chunks=int(self._state.render_distance_chunks))

    def _respawn(self) -> None:
        self._session.respawn()
        self._invalidate_selection_target()
        self._renderer.clear_selection()
        self._overlays.set_dead(False)

    def _resume_from_overlay(self) -> None:
        self._overlays.set_paused(False)
        self._sync_cloud_motion_pause()

    def _open_settings_from_pause(self) -> None:
        self._sync_settings_values()
        self._overlays.set_settings_open(True)
        self._sync_cloud_motion_pause()

    def _back_from_settings(self) -> None:
        self._sync_settings_values()
        self._overlays.set_settings_open(False)
        self._sync_cloud_motion_pause()

    def _set_fov(self, fov: float) -> None:
        self._session.settings.set_fov(float(fov))

    def _set_sens(self, sens: float) -> None:
        self._session.settings.set_mouse_sens(float(sens))

    def _set_invert_x(self, on: bool) -> None:
        self._state.invert_x = bool(on)

    def _set_invert_y(self, on: bool) -> None:
        self._state.invert_y = bool(on)

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
            self._session.player.flying = False
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _set_auto_jump(self, on: bool) -> None:
        self._state.auto_jump_enabled = bool(on)

    def _set_auto_sprint(self, on: bool) -> None:
        self._state.auto_sprint_enabled = bool(on)

    def _set_gravity(self, gravity: float) -> None:
        self._session.settings.set_gravity(float(gravity))

    def _set_walk_speed(self, walk_speed: float) -> None:
        self._session.settings.set_walk_speed(float(walk_speed))

    def _set_sprint_speed(self, sprint_speed: float) -> None:
        self._session.settings.set_sprint_speed(float(sprint_speed))

    def _set_jump_v0(self, jump_v0: float) -> None:
        self._session.settings.set_jump_v0(float(jump_v0))

    def _set_auto_jump_cooldown_s(self, cooldown_s: float) -> None:
        self._session.settings.set_auto_jump_cooldown_s(float(cooldown_s))

    def _set_fly_speed(self, fly_speed: float) -> None:
        self._session.settings.set_fly_speed(float(fly_speed))

    def _set_fly_ascend_speed(self, fly_ascend_speed: float) -> None:
        self._session.settings.set_fly_ascend_speed(float(fly_ascend_speed))

    def _set_fly_descend_speed(self, fly_descend_speed: float) -> None:
        self._session.settings.set_fly_descend_speed(float(fly_descend_speed))

    def _reset_advanced_defaults(self) -> None:
        self._session.settings.reset_advanced_movement_defaults()
        self._sync_settings_values()

    def _set_render_distance(self, v: int) -> None:
        self._state.render_distance_chunks = int(v)
        self._state.normalize()

    def _on_inventory_selected(self, block_id: str) -> None:
        if not bool(self._state.creative_mode):
            return
        active_index = int(self._state.creative_selected_hotbar_index if bool(self._state.creative_mode) else self._state.survival_selected_hotbar_index)
        self._state.set_hotbar_slot(int(active_index), str(block_id))
        self._sync_hotbar_widgets()
        self._sync_first_person_target()

    def _on_inventory_closed(self) -> None:
        self._overlays.set_inventory_open(False)

    def _on_step(self, dt: float) -> None:
        self._inp.poll_relative_mouse_delta()
        fr, md = self._inp.consume(invert_x=self._state.invert_x, invert_y=self._state.invert_y)

        if float(self._session.player.position.y) < -64.0:
            self._overlays.set_dead(True)
            return

        sprint = bool(fr.sprint)
        if bool(self._state.auto_sprint_enabled):
            if float(fr.move_f) > 1e-6 and (not bool(fr.crouch)):
                sprint = True

        jump_started = self._session.step(dt=float(dt), move_f=fr.move_f, move_s=fr.move_s, jump_held=bool(fr.jump_held), jump_pressed=bool(fr.jump_pressed), sprint=bool(sprint), crouch=bool(fr.crouch), mdx=float(md.dx), mdy=float(md.dy), creative_mode=bool(self._state.creative_mode), auto_jump_enabled=bool(self._state.auto_jump_enabled))
        self._sync_first_person_target()
        self._first_person_motion.update(float(dt))
        self._hud_ctl.on_sim_step(dt=float(dt), player=self._session.player, jump_started=bool(jump_started))

        if float(self._session.player.position.y) < -64.0:
            self._overlays.set_dead(True)
            return

        if not self._hud_ctl.should_emit():
            return

        if not bool(self._state.hud_visible):
            return

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        payload = self._hud_ctl.build_payload(session=self._session, renderer=self._renderer, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, creative_mode=self._state.creative_mode, flying=bool(self._session.player.flying), inventory_open=self._overlays.inventory_open(), selected_block_id=self._current_block_id() or "", reach=self._state.reach, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, shadow_enabled=self._state.shadow_enabled, world_wire=self._state.world_wire, cloud_wire=self._state.cloud_wire, cloud_enabled=self._state.cloud_enabled, cloud_density=self._state.cloud_density, cloud_seed=self._state.cloud_seed, debug_shadow=self._state.debug_shadow, fb_w=fb_w, fb_h=fb_h, dpr=dpr, vsync_on=self._state.vsync_on, render_timer_interval_ms=int(self._render_timer.interval()), sim_hz=float(self._loop.sim_hz), render_distance_chunks=int(self._state.render_distance_chunks), paint_ms=float(self._last_paint_ms), selection_pick_ms=float(self._last_selection_pick_ms))
        self.hud_updated.emit(payload)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        hotbar_idx = hotbar_index_from_key(int(e.key()))
        if hotbar_idx is not None and (not self._overlays.paused()) and (not self._overlays.dead()) and (not self._overlays.settings_open()):
            if not self._overlays.inventory_open():
                self._select_hotbar_slot(int(hotbar_idx))
                return

        if int(e.key()) == int(Qt.Key.Key_F4):
            self._state.debug_shadow = not bool(self._state.debug_shadow)
            self._renderer.set_debug_shadow(bool(self._state.debug_shadow))
            return

        if int(e.key()) == int(Qt.Key.Key_F3):
            self._state.hud_visible = not bool(self._state.hud_visible)
            if self._hud is not None:
                self._hud.setVisible(bool(self._state.hud_visible))
                if bool(self._state.hud_visible):
                    self._hud.raise_()
            return

        if int(e.key()) == int(Qt.Key.Key_Escape):
            if self._overlays.dead():
                return

            if self._overlays.inventory_open():
                self._overlays.set_inventory_open(False)
                return

            if self._overlays.settings_open():
                self._back_from_settings()
                return

            if self._overlays.paused():
                self._overlays.set_paused(False)
                self._sync_cloud_motion_pause()
            else:
                self._sync_settings_values()
                self._overlays.set_paused(True)
                self._sync_cloud_motion_pause()
            return

        if int(e.key()) == int(Qt.Key.Key_B) and (not self._overlays.paused()) and (not self._overlays.dead()):
            self._set_creative_mode(not self._state.creative_mode)
            self._sync_settings_values()
            return

        if int(e.key()) == int(Qt.Key.Key_E) and (not self._overlays.paused()) and (not self._overlays.dead()):
            self._overlays.set_inventory_open(not self._overlays.inventory_open())
            return

        if (not self._overlays.paused()) and (not self._overlays.inventory_open()) and (not self._overlays.dead()):
            self._inp.on_key_press(e)

        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open():
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

        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead():
            super().mousePressEvent(e)
            return

        if not self._inp.captured():
            self._inp.set_mouse_capture(True)
            super().mousePressEvent(e)
            return

        b = e.button()
        if b == Qt.MouseButton.LeftButton:
            self._session.break_block(reach=float(self._state.reach))
            self._first_person_motion.trigger_left_swing()
            self._invalidate_selection_target()
        elif b == Qt.MouseButton.RightButton:
            success = self._session.place_block(block_id=self._current_block_id(), reach=float(self._state.reach), crouching=bool(self._inp.crouch_held()))
            self._first_person_motion.trigger_right_swing(success=bool(success))
            if bool(success):
                self._invalidate_selection_target()

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or (not self._inp.captured()):
            super().mouseMoveEvent(e)
            return

        e.accept()
        return