# FILE: presentation/widgets/glViewportWidget.py
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QSurfaceFormat, QCursor

from core.math.vec3 import Vec3
from application.session.fixedStepRunner import FixedStepRunner
from application.session.sessionManager import SessionManager
from infrastructure.platform.qtInputAdapter import QtInputAdapter
from infrastructure.rendering.opengl.glRenderer import GLRenderer
from infrastructure.persistence.appStateStore import (
    AppStateStore,
    AppState,
    PersistedSettings,
    PersistedWorld,
    PersistedPlayer,
)
from presentation.widgets.pauseOverlay import PauseOverlay
from presentation.widgets.crosshairWidget import CrosshairWidget
from presentation.widgets.inventoryOverlay import InventoryOverlay
from presentation.widgets.deathOverlay import DeathOverlay
from presentation.config.gameLoopParams import GameLoopParams, DEFAULT_GAME_LOOP_PARAMS

class GLViewportWidget(QOpenGLWidget):
    hud_updated = pyqtSignal(str)

    def __init__(self, project_root: Path, parent=None, loop_params: GameLoopParams = DEFAULT_GAME_LOOP_PARAMS) -> None:
        super().__init__(parent)
        self._project_root = project_root
        self._assets_dir = project_root / "assets"
        self._loop = loop_params

        self._input = QtInputAdapter(self)
        self._session = SessionManager.create_default(seed=0)
        self._runner = FixedStepRunner(step_dt=self._loop.step_dt(), on_step=self._on_step)

        self._renderer = GLRenderer()
        self._hud = None
        self._world_uploaded = -1

        self._captured = False

        self._paused = False
        self._dead = False

        self._invert_x = False
        self._invert_y = False
        self._cloud_wire = False

        self._cloud_enabled = True
        self._cloud_density = 1
        self._cloud_seed = 1337

        self._world_wire = False
        self._shadow_enabled = True

        self._build_mode = False
        self._inventory_open = False
        self._selected_block_id = "minecraft:grass_block"
        self._reach = 5.0

        self._auto_jump_enabled = False

        az, el = self._renderer.sun_angles()
        self._sun_az_deg = float(az)
        self._sun_el_deg = float(el)

        self._debug_shadow = False
        self._renderer.set_debug_shadow(self._debug_shadow)

        self._overlay = PauseOverlay(self)
        self._overlay.resume_requested.connect(self._resume_from_overlay)
        self._overlay.fov_changed.connect(self._set_fov)
        self._overlay.sens_changed.connect(self._set_sens)
        self._overlay.invert_x_changed.connect(self._set_invert_x)
        self._overlay.invert_y_changed.connect(self._set_invert_y)
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

        self._death = DeathOverlay(self)
        self._death.respawn_requested.connect(self._respawn)

        self._crosshair = CrosshairWidget(self)
        self._crosshair.setVisible(True)

        self._inventory = InventoryOverlay(self)
        self._inventory.block_selected.connect(self._on_inventory_selected)
        self._inventory.closed.connect(self._on_inventory_closed)

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

        self._fps_render = 0.0
        self._fps_sim = 0.0
        self._fps_window_t0 = time.perf_counter()
        self._fps_render_frames = 0
        self._fps_sim_steps = 0

        self._hud_emit_last_t = 0.0
        self._hud_emit_interval_s = 0.10

        self._apply_persisted_state_if_present()

    def _apply_persisted_state_if_present(self) -> None:
        store = AppStateStore(project_root=self._project_root)
        st = store.load()
        if st is None:
            return

        ps = st.settings
        self._session.settings.set_fov(float(ps.fov_deg))
        self._session.settings.set_mouse_sens(float(ps.mouse_sens_deg_per_px))

        self._invert_x = bool(ps.invert_x)
        self._invert_y = bool(ps.invert_y)

        self._world_wire = bool(ps.world_wireframe)
        self._shadow_enabled = bool(ps.shadow_enabled)

        self._sun_az_deg = float(ps.sun_az_deg)
        self._sun_el_deg = float(ps.sun_el_deg)

        self._cloud_enabled = bool(ps.cloud_enabled)
        self._cloud_density = int(max(0, min(4, int(ps.cloud_density))))
        self._cloud_seed = int(max(0, min(9999, int(ps.cloud_seed))))

        self._build_mode = bool(ps.build_mode)
        self._auto_jump_enabled = bool(ps.auto_jump_enabled)

        if not bool(self._build_mode):
            self._inventory_open = False

        pp = st.player
        p = self._session.player
        p.position = Vec3(float(pp.pos_x), float(pp.pos_y), float(pp.pos_z))
        p.velocity = Vec3(float(pp.vel_x), float(pp.vel_y), float(pp.vel_z))
        p.yaw_deg = float(pp.yaw_deg)
        p.pitch_deg = float(pp.pitch_deg)
        p.clamp_pitch()
        p.on_ground = bool(pp.on_ground)
        p.crouch_eye_offset = float(max(0.0, min(float(p.crouch_eye_drop), float(pp.crouch_eye_offset))))
        p.hold_jump_queued = False
        p.auto_jump_pending = False
        p.auto_jump_cooldown_s = 0.0
        p.auto_jump_start_y = float(p.position.y)

        pw = st.world
        if pw.blocks:
            self._session.world.blocks.clear()
            for (x, y, z), s in pw.blocks.items():
                self._session.world.blocks[(int(x), int(y), int(z))] = str(s)
            self._session.world.revision = int(max(1, int(pw.revision)))

        self._renderer.set_world_wireframe(self._world_wire)
        self._renderer.set_shadow_enabled(self._shadow_enabled)
        self._renderer.set_sun_angles(self._sun_az_deg, self._sun_el_deg)

        self._renderer.set_cloud_wireframe(self._cloud_wire)
        self._renderer.set_cloud_enabled(self._cloud_enabled)
        self._renderer.set_cloud_density(self._cloud_density)
        self._renderer.set_cloud_seed(self._cloud_seed)

    def save_state(self) -> None:
        store = AppStateStore(project_root=self._project_root)

        settings = PersistedSettings(
            fov_deg=float(self._session.settings.fov_deg),
            mouse_sens_deg_per_px=float(self._session.settings.mouse_sens_deg_per_px),
            invert_x=bool(self._invert_x),
            invert_y=bool(self._invert_y),
            world_wireframe=bool(self._world_wire),
            shadow_enabled=bool(self._shadow_enabled),
            sun_az_deg=float(self._sun_az_deg),
            sun_el_deg=float(self._sun_el_deg),
            cloud_enabled=bool(self._cloud_enabled),
            cloud_density=int(self._cloud_density),
            cloud_seed=int(self._cloud_seed),
            build_mode=bool(self._build_mode),
            auto_jump_enabled=bool(self._auto_jump_enabled),
        )

        pl = self._session.player
        player = PersistedPlayer(
            pos_x=float(pl.position.x),
            pos_y=float(pl.position.y),
            pos_z=float(pl.position.z),
            vel_x=float(pl.velocity.x),
            vel_y=float(pl.velocity.y),
            vel_z=float(pl.velocity.z),
            yaw_deg=float(pl.yaw_deg),
            pitch_deg=float(pl.pitch_deg),
            on_ground=bool(pl.on_ground),
            jump_cooldown_s=0.0,
            crouch_eye_offset=float(max(0.0, min(float(pl.crouch_eye_drop), float(pl.crouch_eye_offset)))),
        )

        world = PersistedWorld(
            revision=int(self._session.world.revision),
            blocks={k: str(v) for (k, v) in self._session.world.blocks.items()},
        )

        state = AppState(version=2, settings=settings, player=player, world=world)
        store.save(state)

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
        self._hud.move(10, 10)
        self._hud.show()
        self._hud.raise_()

    def initializeGL(self) -> None:
        self._renderer.initialize(self._assets_dir)

        self._renderer.set_cloud_wireframe(self._cloud_wire)
        self._renderer.set_cloud_enabled(self._cloud_enabled)
        self._renderer.set_cloud_density(self._cloud_density)
        self._renderer.set_cloud_seed(self._cloud_seed)

        self._renderer.set_shadow_enabled(self._shadow_enabled)
        self._renderer.set_world_wireframe(self._world_wire)
        self._renderer.set_sun_angles(self._sun_az_deg, self._sun_el_deg)

        self._runner.start()
        self._sim_timer.start()
        self._render_timer.start()

    def resizeGL(self, w: int, h: int) -> None:
        if self._hud is not None:
            self._hud.move(10, 10)
            self._hud.raise_()
        self._overlay.setGeometry(0, 0, max(1, w), max(1, h))
        self._crosshair.setGeometry(0, 0, max(1, w), max(1, h))
        self._inventory.setGeometry(0, 0, max(1, w), max(1, h))
        self._death.setGeometry(0, 0, max(1, w), max(1, h))

        if self._dead:
            self._death.raise_()
        elif self._paused:
            self._overlay.raise_()
        elif self._inventory_open:
            self._inventory.raise_()
        else:
            self._crosshair.raise_()

    def paintGL(self) -> None:
        self._fps_render_frames += 1
        self._maybe_update_fps()

        snap = self._session.make_snapshot()

        if int(snap.world_revision) != int(self._world_uploaded):
            blocks = [(b.x, b.y, b.z, b.block_id) for b in snap.blocks]
            self._renderer.submit_world(world_revision=int(snap.world_revision), blocks=blocks)
            self._world_uploaded = int(snap.world_revision)

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
        )

    def _tick_sim(self) -> None:
        if self._dead:
            return
        if not self._paused and not self._inventory_open:
            self._runner.update()

    def _maybe_update_fps(self) -> None:
        now = time.perf_counter()
        dt = float(now - self._fps_window_t0)
        if dt < 0.5:
            return

        self._fps_render = float(self._fps_render_frames) / dt if dt > 1e-9 else 0.0
        self._fps_sim = float(self._fps_sim_steps) / dt if dt > 1e-9 else 0.0

        self._fps_window_t0 = now
        self._fps_render_frames = 0
        self._fps_sim_steps = 0

    def _center_global(self) -> QPoint:
        c = QPoint(self.width() // 2, self.height() // 2)
        return self.mapToGlobal(c)

    def _set_mouse_capture(self, on: bool) -> None:
        if on == self._captured:
            return
        self._captured = bool(on)

        if self._captured:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.grabMouse()
            self.grabKeyboard()
            QCursor.setPos(self._center_global())
        else:
            self.releaseKeyboard()
            self.releaseMouse()
            self.unsetCursor()

    def _poll_relative_mouse_delta(self) -> None:
        if not self._captured:
            return

        center = self._center_global()
        cur = QCursor.pos()
        dx = float(cur.x() - center.x())
        dy = float(cur.y() - center.y())

        if dx == 0.0 and dy == 0.0:
            return

        self._input.add_mouse_delta(dx, dy)
        QCursor.setPos(center)

    def _sync_overlay_values(self) -> None:
        az, el = self._renderer.sun_angles()
        self._sun_az_deg = float(az)
        self._sun_el_deg = float(el)

        self._overlay.sync_values(
            fov_deg=self._session.settings.fov_deg,
            sens_deg_per_px=self._session.settings.mouse_sens_deg_per_px,
            inv_x=self._invert_x,
            inv_y=self._invert_y,
            cloud_wire=self._cloud_wire,
            clouds_enabled=self._cloud_enabled,
            cloud_density=int(self._cloud_density),
            cloud_seed=int(self._cloud_seed),
            world_wire=self._world_wire,
            shadow_enabled=self._shadow_enabled,
            sun_az_deg=self._sun_az_deg,
            sun_el_deg=self._sun_el_deg,
            build_mode=self._build_mode,
            auto_jump_enabled=self._auto_jump_enabled,
        )

    def _set_dead(self, on: bool) -> None:
        on = bool(on)
        if on == self._dead:
            return
        self._dead = on

        self._input.reset()

        if self._dead:
            self._paused = False
            self._overlay.setVisible(False)
            self._set_inventory_open(False)
            self._set_mouse_capture(False)

            self._death.setVisible(True)
            self._death.raise_()
        else:
            self._death.setVisible(False)
            self._runner.start()
            if not self._paused and not self._inventory_open:
                self._set_mouse_capture(True)
            self._crosshair.raise_()
            if self._hud is not None:
                self._hud.raise_()

    def _respawn(self) -> None:
        self._session.respawn()
        self._set_dead(False)

    def _set_paused(self, on: bool) -> None:
        if on == self._paused:
            return
        if self._dead:
            return

        self._paused = bool(on)

        self._input.reset()

        if self._paused:
            self._set_inventory_open(False)
            self._set_mouse_capture(False)
            self._sync_overlay_values()
            self._overlay.setVisible(True)
            self._overlay.raise_()
        else:
            self._overlay.setVisible(False)
            self._runner.start()
            if not self._inventory_open:
                self._set_mouse_capture(True)
            self._crosshair.raise_()
            if self._hud is not None:
                self._hud.raise_()

    def _set_inventory_open(self, on: bool) -> None:
        on = bool(on)
        if on == self._inventory_open:
            return
        self._inventory_open = on

        self._input.reset()

        if self._inventory_open:
            self._set_mouse_capture(False)
            self._inventory.setVisible(True)
            self._inventory.raise_()
            self._inventory.setFocus()
        else:
            self._inventory.setVisible(False)
            if not self._paused and not self._dead:
                self._runner.start()
                self._set_mouse_capture(True)
                self._crosshair.raise_()
                if self._hud is not None:
                    self._hud.raise_()

    def _resume_from_overlay(self) -> None:
        self._set_paused(False)

    def _set_fov(self, fov: float) -> None:
        self._session.settings.set_fov(float(fov))

    def _set_sens(self, sens: float) -> None:
        self._session.settings.set_mouse_sens(float(sens))

    def _set_invert_x(self, on: bool) -> None:
        self._invert_x = bool(on)

    def _set_invert_y(self, on: bool) -> None:
        self._invert_y = bool(on)

    def _set_cloud_wire(self, on: bool) -> None:
        self._cloud_wire = bool(on)
        self._renderer.set_cloud_wireframe(self._cloud_wire)

    def _set_cloud_enabled(self, on: bool) -> None:
        self._cloud_enabled = bool(on)
        self._renderer.set_cloud_enabled(self._cloud_enabled)

    def _set_cloud_density(self, v: int) -> None:
        self._cloud_density = int(max(0, min(4, int(v))))
        self._renderer.set_cloud_density(self._cloud_density)

    def _set_cloud_seed(self, v: int) -> None:
        self._cloud_seed = int(max(0, min(9999, int(v))))
        self._renderer.set_cloud_seed(self._cloud_seed)

    def _set_world_wire(self, on: bool) -> None:
        self._world_wire = bool(on)
        self._renderer.set_world_wireframe(self._world_wire)

    def _set_shadow_enabled(self, on: bool) -> None:
        self._shadow_enabled = bool(on)
        self._renderer.set_shadow_enabled(self._shadow_enabled)

    def _set_sun_azimuth(self, az_deg: float) -> None:
        self._sun_az_deg = float(az_deg)
        self._renderer.set_sun_angles(self._sun_az_deg, self._sun_el_deg)

    def _set_sun_elevation(self, el_deg: float) -> None:
        self._sun_el_deg = float(el_deg)
        self._renderer.set_sun_angles(self._sun_az_deg, self._sun_el_deg)

    def _set_build_mode(self, on: bool) -> None:
        self._build_mode = bool(on)
        if not bool(self._build_mode):
            self._set_inventory_open(False)

    def _set_auto_jump(self, on: bool) -> None:
        self._auto_jump_enabled = bool(on)

    def _on_inventory_selected(self, block_id: str) -> None:
        self._selected_block_id = str(block_id)

    def _on_inventory_closed(self) -> None:
        self._set_inventory_open(False)

    def _on_step(self, dt: float) -> None:
        self._fps_sim_steps += 1
        self._maybe_update_fps()

        self._poll_relative_mouse_delta()
        fr = self._input.consume()

        mdx = fr.mdx
        mdy = fr.mdy
        if self._invert_x:
            mdx = -mdx
        if self._invert_y:
            mdy = -mdy

        if float(self._session.player.position.y) < -64.0:
            self._set_dead(True)
            return

        self._session.step(
            dt=float(dt),
            move_f=fr.move_f,
            move_s=fr.move_s,
            jump_held=bool(fr.jump_held),
            jump_pressed=bool(fr.jump_pressed),
            sprint=bool(fr.sprint),
            crouch=bool(fr.crouch),
            mdx=float(mdx),
            mdy=float(mdy),
            auto_jump_enabled=bool(self._auto_jump_enabled),
        )

        if float(self._session.player.position.y) < -64.0:
            self._set_dead(True)
            return

        now = time.perf_counter()
        if (now - float(self._hud_emit_last_t)) < float(self._hud_emit_interval_s):
            return
        self._hud_emit_last_t = now

        shadow_ok, shadow_size = self._renderer.shadow_info()
        mode = self._renderer.shadow_status_text()

        p = self._session.player
        hs = (float(p.velocity.x) * float(p.velocity.x) + float(p.velocity.z) * float(p.velocity.z)) ** 0.5

        hud = (
            f"FPS: render={self._fps_render:.1f} sim={self._fps_sim:.1f}\n"
            "WASD: move | Space: jump (hold-jump enabled) | Shift: crouch | Ctrl: sprint | Click: capture mouse | ESC: pause/menu | F3: shadow debug view\n"
            "B: build mode | E: inventory | LMB: break | RMB: place\n"
            f"pos=({p.position.x:.2f},{p.position.y:.2f},{p.position.z:.2f}) "
            f"vel=({p.velocity.x:.2f},{p.velocity.y:.2f},{p.velocity.z:.2f}) "
            f"hs={hs:.3f} ground={int(p.on_ground)} yaw={p.yaw_deg:.1f} pitch={p.pitch_deg:.1f} "
            f"fov={self._session.settings.fov_deg:.0f} sens={self._session.settings.mouse_sens_deg_per_px:.3f}\n"
            f"autoJump={int(self._auto_jump_enabled)} autoJumpCD={p.auto_jump_cooldown_s:.2f} "
            f"build={int(self._build_mode)} inv={int(self._inventory_open)} sel={self._selected_block_id} reach={self._reach:.1f} "
            f"sunAz={self._sun_az_deg:.0f} sunEl={self._sun_el_deg:.0f} "
            f"shadowEn={int(self._shadow_enabled)} worldWire={int(self._world_wire)} cloudWire={int(self._cloud_wire)} "
            f"cloudEn={int(self._cloud_enabled)} cloudDen={int(self._cloud_density)} cloudSeed={int(self._cloud_seed)} "
            f"shadow={int(shadow_ok)} size={int(shadow_size)} mode={mode} dbg={int(self._debug_shadow)}"
        )
        self.hud_updated.emit(hud)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if int(e.key()) == int(Qt.Key.Key_F3):
            self._debug_shadow = not self._debug_shadow
            self._renderer.set_debug_shadow(self._debug_shadow)
            return

        if int(e.key()) == int(Qt.Key.Key_Escape):
            if self._dead:
                return
            if self._inventory_open:
                self._set_inventory_open(False)
                return
            self._set_paused(not self._paused)
            return

        if int(e.key()) == int(Qt.Key.Key_B) and (not self._paused) and (not self._dead):
            self._set_build_mode(not self._build_mode)
            self._sync_overlay_values()
            return

        if int(e.key()) == int(Qt.Key.Key_E) and (not self._paused) and (not self._dead) and bool(self._build_mode):
            self._set_inventory_open(not self._inventory_open)
            return

        if not self._paused and not self._inventory_open and not self._dead:
            self._input.on_key_press(e)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        self._input.on_key_release(e)
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if self._paused or self._inventory_open or self._dead:
            super().mousePressEvent(e)
            return

        if not self._captured:
            self._set_mouse_capture(True)
            super().mousePressEvent(e)
            return

        if bool(self._build_mode):
            b = e.button()
            if b == Qt.MouseButton.LeftButton:
                self._session.break_block(reach=float(self._reach))
            elif b == Qt.MouseButton.RightButton:
                self._session.place_block(block_id=self._selected_block_id, reach=float(self._reach))

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._paused or self._inventory_open or self._dead or not self._captured:
            super().mouseMoveEvent(e)
            return

        e.accept()
        return