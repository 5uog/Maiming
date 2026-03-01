# FILE: src/maiming/presentation/widgets/viewport/viewport_hud.py
from __future__ import annotations

import time
from dataclasses import dataclass

from maiming.core.math.vec3 import Vec3
from maiming.application.session.session_manager import SessionManager
from maiming.infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer

@dataclass
class HudFps:
    render_fps: float
    sim_fps: float

class ViewportHud:
    """
    This module owns the time-windowed FPS estimator and the HUD text assembly.
    The implementation keeps the original formatting stable so downstream UI sizing
    and user expectations remain unchanged under refactoring.
    """
    def __init__(self) -> None:
        self._fps_render: float = 0.0
        self._fps_sim: float = 0.0
        self._fps_window_t0: float = time.perf_counter()
        self._fps_render_frames: int = 0
        self._fps_sim_steps: int = 0

        self._hud_emit_last_t: float = 0.0
        self._hud_emit_interval_s: float = 0.10

    def on_render_frame(self) -> None:
        self._fps_render_frames += 1
        self._maybe_update_fps()

    def on_sim_step(self) -> None:
        self._fps_sim_steps += 1
        self._maybe_update_fps()

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

    def fps(self) -> HudFps:
        return HudFps(render_fps=float(self._fps_render), sim_fps=float(self._fps_sim))

    def should_emit(self) -> bool:
        now = time.perf_counter()
        if (now - float(self._hud_emit_last_t)) < float(self._hud_emit_interval_s):
            return False
        self._hud_emit_last_t = now
        return True

    def build_text(
        self,
        *,
        session: SessionManager,
        renderer: GLRenderer,
        auto_jump_enabled: bool,
        build_mode: bool,
        inventory_open: bool,
        selected_block_id: str,
        reach: float,
        sun_az_deg: float,
        sun_el_deg: float,
        shadow_enabled: bool,
        world_wire: bool,
        cloud_wire: bool,
        cloud_enabled: bool,
        cloud_density: int,
        cloud_seed: int,
        debug_shadow: bool,
    ) -> str:
        fps = self.fps()

        shadow_ok, shadow_size = renderer.shadow_info()
        mode = renderer.shadow_status_text()

        p = session.player
        hs = (float(p.velocity.x) * float(p.velocity.x) + float(p.velocity.z) * float(p.velocity.z)) ** 0.5

        return (
            f"FPS: render={fps.render_fps:.1f} sim={fps.sim_fps:.1f}\n"
            "WASD: move | Space: jump (hold-jump enabled) | Shift: crouch | Ctrl: sprint | Click: capture mouse | ESC: pause/menu | F3: shadow debug view\n"
            "B: build mode | E: inventory | LMB: break | RMB: place\n"
            f"pos=({p.position.x:.2f},{p.position.y:.2f},{p.position.z:.2f}) "
            f"vel=({p.velocity.x:.2f},{p.velocity.y:.2f},{p.velocity.z:.2f}) "
            f"hs={hs:.3f} ground={int(p.on_ground)} yaw={p.yaw_deg:.1f} pitch={p.pitch_deg:.1f} "
            f"fov={session.settings.fov_deg:.0f} sens={session.settings.mouse_sens_deg_per_px:.3f}\n"
            f"autoJump={int(bool(auto_jump_enabled))} autoJumpCD={p.auto_jump_cooldown_s:.2f} "
            f"build={int(bool(build_mode))} inv={int(bool(inventory_open))} sel={str(selected_block_id)} reach={float(reach):.1f} "
            f"sunAz={float(sun_az_deg):.0f} sunEl={float(sun_el_deg):.0f} "
            f"shadowEn={int(bool(shadow_enabled))} worldWire={int(bool(world_wire))} cloudWire={int(bool(cloud_wire))} "
            f"cloudEn={int(bool(cloud_enabled))} cloudDen={int(cloud_density)} cloudSeed={int(cloud_seed)} "
            f"shadow={int(shadow_ok)} size={int(shadow_size)} mode={mode} dbg={int(bool(debug_shadow))}"
        )