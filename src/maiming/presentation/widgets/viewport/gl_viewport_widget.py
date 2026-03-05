# FILE: src/maiming/presentation/widgets/viewport/gl_viewport_widget.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QSurfaceFormat

from maiming.core.math.vec3 import Vec3
from maiming.application.session.fixed_step_runner import FixedStepRunner
from maiming.application.session.session_manager import SessionManager
from maiming.infrastructure.platform.qt_input_adapter import QtInputAdapter
from maiming.infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer

from maiming.presentation.widgets.overlays.pause_overlay import PauseOverlay
from maiming.presentation.widgets.hud.crosshair_widget import CrosshairWidget
from maiming.presentation.widgets.overlays.inventory_overlay import InventoryOverlay
from maiming.presentation.widgets.overlays.death_overlay import DeathOverlay
from maiming.presentation.config.game_loop_params import GameLoopParams, DEFAULT_GAME_LOOP_PARAMS

from maiming.presentation.widgets.viewport.viewport_input import ViewportInput
from maiming.presentation.widgets.viewport.viewport_overlays import ViewportOverlays, OverlayRefs
from maiming.presentation.widgets.viewport.viewport_persistence import (
    apply_persisted_state_if_present,
    save_state,
)
from maiming.presentation.widgets.viewport.viewport_world_upload import WorldUploadTracker
from maiming.presentation.widgets.viewport.viewport_runtime_state import ViewportRuntimeState

from maiming.presentation.hud.hud_controller import HudController

class GLViewportWidget(QOpenGLWidget):
    hud_updated = pyqtSignal(object)

    def __init__(
        self,
        project_root: Path,
        parent=None,
        loop_params: GameLoopParams = DEFAULT_GAME_LOOP_PARAMS,
    ) -> None:
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

        self._shutdown_done = False

        self._overlay = PauseOverlay(self)
        self._overlay.resume_requested.connect(self._resume_from_overlay)
        self._overlay.fov_changed.connect(self._set_fov)
        self._overlay.sens_changed.connect(self._set_sens)
        self._overlay.invert_x_changed.connect(self._set_invert_x)
        self._overlay.invert_y_changed.connect(self._set_invert_y)
        self._overlay.outline_selection_changed.connect(self._set_outline_selection)
        self._overlay.cloud_wireframe_changed.connect(self._set_cloud_wire)
        self._overlay.clouds_enabled_changed.connect(self._set_cloud_enabled)
        self._overlay.cloud_density_changed.connect(self._set_cloud_density)
        self._overlay.cloud_seed_changed.connect(self._set_cloud_seed)
        self._overlay.world_wireframe_changed.connect(self._set_world_wire)
        self._overlay.shadow_enabled_changed.connect(self._set_shadow_enabled)
        self._overlay.sun_azimuth_changed.connect(self._set_sun_azimuth)
        self._overlay.sun_elevation_changed.connect(self._set_sun_elevation)
        self._overlay.build_mode_changed.connect(self._set_build_mode)
        self._overlay.auto_jump_changed.connect(self._set_auto_jump)
        self._overlay.auto_sprint_changed.connect(self._set_auto_sprint)
        self._overlay.render_distance_changed.connect(self._set_render_distance)

        self._death = DeathOverlay(self)
        self._death.respawn_requested.connect(self._respawn)

        self._crosshair = CrosshairWidget(self)
        self._crosshair.setVisible(True)

        self._inventory = InventoryOverlay(parent=self, project_root=self._project_root)
        self._inventory.block_selected.connect(self._on_inventory_selected)
        self._inventory.closed.connect(self._on_inventory_closed)

        self._overlays = ViewportOverlays(
            refs=OverlayRefs(
                pause=self._overlay,
                inventory=self._inventory,
                death=self._death,
                crosshair=self._crosshair,
                hud_getter=lambda: self._hud,
            ),
            runner=self._runner,
            inp=self._inp,
        )

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

        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)
        self.setFormat(fmt)

        self._state = apply_persisted_state_if_present(
            project_root=self._project_root,
            session=self._session,
            renderer=self._renderer,
        )
        self._apply_runtime_to_renderer()

        if not bool(self._state.build_mode):
            self._overlays.set_inventory_open(False)

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

        self._renderer.set_shadow_enabled(bool(self._state.shadow_enabled))
        self._renderer.set_world_wireframe(bool(self._state.world_wire))

        self._renderer.set_sun_angles(
            float(self._state.sun_az_deg),
            float(self._state.sun_el_deg),
        )

    def save_state(self) -> None:
        self._sync_state_from_renderer_sun()
        save_state(
            project_root=self._project_root,
            session=self._session,
            renderer=self._renderer,
            runtime=self._state,
        )

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
            self._hud.raise_()

    def initializeGL(self) -> None:
        self._renderer.initialize(self._assets_dir)

        ctx = self.context()
        if ctx is not None:
            try:
                self._state.vsync_on = int(ctx.format().swapInterval()) > 0
            except Exception:
                self._state.vsync_on = False

        self._apply_runtime_to_renderer()

        eye0 = self._session.player.eye_pos()
        self._upload.bootstrap_resident(
            world=self._session.world,
            renderer=self._renderer,
            eye=eye0,
            render_distance_chunks=int(self._state.render_distance_chunks),
        )

        self._runner.start()
        self._sim_timer.start()
        self._render_timer.start()

    def resizeGL(self, w: int, h: int) -> None:
        if self._hud is not None:
            self._hud.setGeometry(0, 0, max(1, w), max(1, h))
            if bool(self._state.hud_visible):
                self._hud.raise_()

        self._overlay.setGeometry(0, 0, max(1, w), max(1, h))
        self._crosshair.setGeometry(0, 0, max(1, w), max(1, h))
        self._inventory.setGeometry(0, 0, max(1, w), max(1, h))
        self._death.setGeometry(0, 0, max(1, w), max(1, h))

        if self._overlays.dead():
            self._death.raise_()
        elif self._overlays.paused():
            self._overlay.raise_()
        elif self._overlays.inventory_open():
            self._inventory.raise_()
        else:
            self._crosshair.raise_()

    def paintGL(self) -> None:
        self._hud_ctl.on_render_frame()

        snap = self._session.make_snapshot()
        eye = Vec3(snap.camera.eye_x, snap.camera.eye_y, snap.camera.eye_z)

        self._upload.upload_if_needed(
            world=self._session.world,
            renderer=self._renderer,
            eye=eye,
            render_distance_chunks=int(self._state.render_distance_chunks),
        )

        from maiming.domain.systems.build_system import pick_block

        hit = pick_block(
            self._session.world,
            origin=eye,
            direction=self._session.player.view_forward(),
            reach=float(self._state.reach),
        )
        if hit is None:
            self._renderer.clear_selection()
        else:
            hx, hy, hz = hit.hit
            st = self._session.world.blocks.get((int(hx), int(hy), int(hz)))
            if st is None:
                self._renderer.clear_selection()
            else:
                def get_state(x: int, y: int, z: int) -> str | None:
                    return self._session.world.blocks.get((int(x), int(y), int(z)))

                self._renderer.set_selection_target(
                    x=int(hx),
                    y=int(hy),
                    z=int(hz),
                    state_str=str(st),
                    get_state=get_state,
                    world_revision=int(self._session.world.revision),
                )

        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))

        cam = snap.camera
        self._renderer.render(
            w=fb_w,
            h=fb_h,
            eye=Vec3(cam.eye_x, cam.eye_y, cam.eye_z),
            yaw_deg=cam.yaw_deg,
            pitch_deg=cam.pitch_deg,
            fov_deg=cam.fov_deg,
            render_distance_chunks=int(self._state.render_distance_chunks),
        )

    def _tick_sim(self) -> None:
        if self._overlays.dead():
            return
        if (not self._overlays.paused()) and (not self._overlays.inventory_open()):
            self._runner.update()

    def _sync_overlay_values(self) -> None:
        self._sync_state_from_renderer_sun()

        self._overlay.sync_values(
            fov_deg=self._session.settings.fov_deg,
            sens_deg_per_px=self._session.settings.mouse_sens_deg_per_px,
            inv_x=self._state.invert_x,
            inv_y=self._state.invert_y,
            outline_selection=self._state.outline_selection,
            cloud_wire=self._state.cloud_wire,
            clouds_enabled=self._state.cloud_enabled,
            cloud_density=int(self._state.cloud_density),
            cloud_seed=int(self._state.cloud_seed),
            world_wire=self._state.world_wire,
            shadow_enabled=self._state.shadow_enabled,
            sun_az_deg=self._state.sun_az_deg,
            sun_el_deg=self._state.sun_el_deg,
            build_mode=self._state.build_mode,
            auto_jump_enabled=self._state.auto_jump_enabled,
            auto_sprint_enabled=self._state.auto_sprint_enabled,
            render_distance_chunks=int(self._state.render_distance_chunks),
        )

    def _respawn(self) -> None:
        self._session.respawn()
        self._overlays.set_dead(False)

    def _resume_from_overlay(self) -> None:
        self._overlays.set_paused(False)

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

    def _set_world_wire(self, on: bool) -> None:
        self._state.world_wire = bool(on)
        self._renderer.set_world_wireframe(bool(self._state.world_wire))

    def _set_shadow_enabled(self, on: bool) -> None:
        self._state.shadow_enabled = bool(on)
        self._renderer.set_shadow_enabled(bool(self._state.shadow_enabled))

    def _set_sun_azimuth(self, az_deg: float) -> None:
        self._state.sun_az_deg = float(az_deg)
        self._state.normalize()
        self._renderer.set_sun_angles(
            float(self._state.sun_az_deg),
            float(self._state.sun_el_deg),
        )

    def _set_sun_elevation(self, el_deg: float) -> None:
        self._state.sun_el_deg = float(el_deg)
        self._state.normalize()
        self._renderer.set_sun_angles(
            float(self._state.sun_az_deg),
            float(self._state.sun_el_deg),
        )

    def _set_build_mode(self, on: bool) -> None:
        self._state.build_mode = bool(on)
        if not bool(self._state.build_mode):
            self._overlays.set_inventory_open(False)

    def _set_auto_jump(self, on: bool) -> None:
        self._state.auto_jump_enabled = bool(on)

    def _set_auto_sprint(self, on: bool) -> None:
        self._state.auto_sprint_enabled = bool(on)

    def _set_render_distance(self, v: int) -> None:
        self._state.render_distance_chunks = int(v)
        self._state.normalize()

    def _on_inventory_selected(self, block_id: str) -> None:
        self._state.selected_block_id = str(block_id)
        self._state.normalize()

    def _on_inventory_closed(self) -> None:
        self._overlays.set_inventory_open(False)

    def _on_step(self, dt: float) -> None:
        self._hud_ctl.on_sim_step()

        self._inp.poll_relative_mouse_delta()
        fr, md = self._inp.consume(
            invert_x=self._state.invert_x,
            invert_y=self._state.invert_y,
        )

        if float(self._session.player.position.y) < -64.0:
            self._overlays.set_dead(True)
            return

        sprint = bool(fr.sprint)
        if bool(self._state.auto_sprint_enabled):
            if float(fr.move_f) > 1e-6 and (not bool(fr.crouch)):
                sprint = True

        self._session.step(
            dt=float(dt),
            move_f=fr.move_f,
            move_s=fr.move_s,
            jump_held=bool(fr.jump_held),
            jump_pressed=bool(fr.jump_pressed),
            sprint=bool(sprint),
            crouch=bool(fr.crouch),
            mdx=float(md.dx),
            mdy=float(md.dy),
            auto_jump_enabled=bool(self._state.auto_jump_enabled),
        )

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

        payload = self._hud_ctl.build_payload(
            session=self._session,
            renderer=self._renderer,
            auto_jump_enabled=self._state.auto_jump_enabled,
            auto_sprint_enabled=self._state.auto_sprint_enabled,
            build_mode=self._state.build_mode,
            inventory_open=self._overlays.inventory_open(),
            selected_block_id=self._state.selected_block_id,
            reach=self._state.reach,
            sun_az_deg=self._state.sun_az_deg,
            sun_el_deg=self._state.sun_el_deg,
            shadow_enabled=self._state.shadow_enabled,
            world_wire=self._state.world_wire,
            cloud_wire=self._state.cloud_wire,
            cloud_enabled=self._state.cloud_enabled,
            cloud_density=self._state.cloud_density,
            cloud_seed=self._state.cloud_seed,
            debug_shadow=self._state.debug_shadow,
            fb_w=fb_w,
            fb_h=fb_h,
            dpr=dpr,
            vsync_on=self._state.vsync_on,
            render_timer_interval_ms=int(self._render_timer.interval()),
            sim_hz=float(self._loop.sim_hz),
            render_distance_chunks=int(self._state.render_distance_chunks),
        )
        self.hud_updated.emit(payload)

    def keyPressEvent(self, e: QKeyEvent) -> None:
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

            if self._overlays.paused():
                self._overlays.set_paused(False)
            else:
                self._sync_overlay_values()
                self._overlays.set_paused(True)
            return

        if int(e.key()) == int(Qt.Key.Key_B) and (not self._overlays.paused()) and (not self._overlays.dead()):
            self._set_build_mode(not self._state.build_mode)
            self._sync_overlay_values()
            return

        if (
            int(e.key()) == int(Qt.Key.Key_E)
            and (not self._overlays.paused())
            and (not self._overlays.dead())
            and bool(self._state.build_mode)
        ):
            self._overlays.set_inventory_open(not self._overlays.inventory_open())
            return

        if (not self._overlays.paused()) and (not self._overlays.inventory_open()) and (not self._overlays.dead()):
            self._inp.on_key_press(e)

        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)

        if self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead():
            super().mousePressEvent(e)
            return

        if not self._inp.captured():
            self._inp.set_mouse_capture(True)
            super().mousePressEvent(e)
            return

        if bool(self._state.build_mode):
            b = e.button()
            if b == Qt.MouseButton.LeftButton:
                self._session.break_block(reach=float(self._state.reach))
            elif b == Qt.MouseButton.RightButton:
                self._session.place_block(
                    block_id=self._state.selected_block_id,
                    reach=float(self._state.reach),
                )

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if (
            self._overlays.paused()
            or self._overlays.inventory_open()
            or self._overlays.dead()
            or (not self._inp.captured())
        ):
            super().mouseMoveEvent(e)
            return

        e.accept()
        return