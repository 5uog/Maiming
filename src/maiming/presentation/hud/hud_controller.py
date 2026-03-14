# FILE: src/maiming/presentation/hud/hud_controller.py
from __future__ import annotations
import math
import time
import tracemalloc
import threading
from dataclasses import dataclass

from ...core.math.vec3 import Vec3
from ...application.session.session_manager import SessionManager
from ...domain.config.render_distance import clamp_render_distance_chunks
from ...infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from ...infrastructure.metrics import SystemInfo, ProcessMemorySnapshot, GpuUtilizationSampler, read_system_info, read_process_memory
from .hud_payload import HudPayload
from .player_metrics import PlayerMetricsTracker
from ...meta import __version__

@dataclass(frozen=True)
class HudFps:
    render_fps: float
    sim_fps: float

@dataclass
class _PyAllocState:
    cur_bytes: int
    peak_bytes: int
    rate_mib_s: float
    last_bytes: int
    last_t: float

@dataclass(frozen=True)
class _ExternalMetrics:
    gpu_util_percent: float | None
    rss_bytes: int | None
    total_bytes: int | None
    updated_t: float

class HudController:
    def __init__(self) -> None:
        self._fps_render: float = 0.0
        self._fps_sim: float = 0.0
        self._fps_window_t0: float = time.perf_counter()
        self._fps_render_frames: int = 0
        self._fps_sim_steps: int = 0

        self._hud_emit_last_t: float = 0.0
        self._hud_emit_interval_s: float = 0.12

        self._sys: SystemInfo = read_system_info()
        self._gpu = GpuUtilizationSampler(min_interval_s=2.0)
        self._metrics = PlayerMetricsTracker(recent_window_s=3.0)

        if not tracemalloc.is_tracing():
            tracemalloc.start()

        now = time.perf_counter()
        cur, peak = tracemalloc.get_traced_memory()
        self._py = _PyAllocState(cur_bytes=int(cur), peak_bytes=int(peak), rate_mib_s=0.0, last_bytes=int(cur), last_t=float(now))
        self._py_last_sample_t: float = float(now)

        self._ext_lock = threading.Lock()
        self._ext = _ExternalMetrics(gpu_util_percent=None, rss_bytes=None, total_bytes=self._sys.total_mem_bytes, updated_t=0.0)

        self._ext_thread = threading.Thread(target=self._external_probe_loop, name="HudExternalProbe", daemon=True)
        self._ext_thread.start()

    def _external_probe_loop(self) -> None:
        while True:
            try:
                snap = read_process_memory(total_mem_bytes=self._sys.total_mem_bytes)
            except Exception:
                snap = ProcessMemorySnapshot(rss_bytes=None, total_bytes=self._sys.total_mem_bytes)

            try:
                gpu = self._gpu.sample()
            except Exception:
                gpu = None

            t = time.perf_counter()
            with self._ext_lock:
                self._ext = _ExternalMetrics(gpu_util_percent=gpu, rss_bytes=snap.rss_bytes, total_bytes=snap.total_bytes if snap.total_bytes is not None else self._sys.total_mem_bytes, updated_t=float(t))

            time.sleep(1.0)

    def on_render_frame(self) -> None:
        self._fps_render_frames += 1
        self._maybe_update_fps()

    def on_sim_step(self, *, dt: float, player, jump_started: bool) -> None:
        self._fps_sim_steps += 1
        self._maybe_update_fps()
        self._metrics.observe_step(dt_s=float(dt), player=player, jump_started=bool(jump_started))

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

    @staticmethod
    def _mib(x_bytes: int | None) -> float | None:
        if x_bytes is None:
            return None
        return float(x_bytes) / (1024.0 * 1024.0)

    @staticmethod
    def _fmt_mib(x_bytes: int | None, digits: int = 0) -> str:
        v = HudController._mib(x_bytes)
        if v is None:
            return "n/a"
        if digits <= 0:
            return f"{v:.0f} MiB"
        return f"{v:.{digits}f} MiB"

    @staticmethod
    def _fmt_optional(v: float | None, digits: int = 3) -> str:
        if v is None:
            return "n/a"
        return f"{float(v):.{digits}f}"

    def _update_py_alloc(self) -> None:
        now = time.perf_counter()
        if (now - float(self._py_last_sample_t)) < 0.35:
            return
        self._py_last_sample_t = float(now)

        cur, peak = tracemalloc.get_traced_memory()
        dt = float(now - float(self._py.last_t))
        dcur = float(int(cur) - int(self._py.last_bytes))
        rate = (dcur / (1024.0 * 1024.0)) / dt if dt > 1e-6 else 0.0
        if rate < 0.0:
            rate = 0.0

        self._py = _PyAllocState(cur_bytes=int(cur), peak_bytes=int(peak), rate_mib_s=float(rate), last_bytes=int(cur), last_t=float(now))

    @staticmethod
    def _cardinal(forward: Vec3) -> str:
        fx = float(forward.x)
        fz = float(forward.z)
        ax = abs(fx)
        az = abs(fz)
        if ax >= az:
            return "E" if fx > 0.0 else "W"
        return "S" if fz > 0.0 else "N"

    @staticmethod
    def _chunk_coords(b: int) -> tuple[int, int]:
        c = int(math.floor(float(b) / 16.0))
        r = int(b - c * 16)
        return c, r

    def _build_left_text(self, *, session: SessionManager, renderer: GLRenderer, auto_jump_enabled: bool, auto_sprint_enabled: bool, creative_mode: bool, flying: bool, inventory_open: bool, selected_block_id: str, reach: float, sun_az_deg: float, sun_el_deg: float, shadow_enabled: bool, world_wire: bool, cloud_wire: bool, cloud_enabled: bool, cloud_density: int, cloud_seed: int, debug_shadow: bool, fb_w: int, fb_h: int, dpr: float, vsync_on: bool, render_timer_interval_ms: int, render_distance_chunks: int, paint_ms: float, selection_pick_ms: float) -> str:
        fps = self.fps()
        t_txt = "inf" if int(render_timer_interval_ms) <= 0 else f"{(1000.0 / float(render_timer_interval_ms)):.0f}"
        vs = "vsync" if bool(vsync_on) else "nosync"

        with self._ext_lock:
            ext = self._ext

        gpu = ext.gpu_util_percent
        gpu_txt = "n/a" if gpu is None else f"{gpu:.0f}%"

        self._update_py_alloc()

        used_bytes = ext.rss_bytes
        used_label = "rss"
        if used_bytes is None or int(used_bytes) <= 0:
            used_bytes = int(max(0, int(self._py.cur_bytes)))
            used_label = "heap"

        total_bytes = ext.total_bytes
        if total_bytes is not None and int(total_bytes) > 0:
            pct = float(used_bytes) / float(total_bytes) * 100.0 if float(total_bytes) > 1.0 else 0.0
            mem_line = f"Mem {pct:.0f}% {self._fmt_mib(int(used_bytes))}/{self._fmt_mib(int(total_bytes))} ({used_label})"
        else:
            mem_line = f"Mem {self._fmt_mib(int(used_bytes))} ({used_label})"

        perf = renderer.frame_metrics()
        world_perf = perf.world
        shadow_perf = perf.shadow

        p = session.player
        px, py, pz = float(p.position.x), float(p.position.y), float(p.position.z)
        bx, by, bz = int(math.floor(px)), int(math.floor(py)), int(math.floor(pz))
        cx, rx = self._chunk_coords(bx)
        cy, _ry = self._chunk_coords(by)
        cz, rz = self._chunk_coords(bz)

        fwd = p.view_forward()
        card = self._cardinal(fwd)

        shadow_ok, shadow_size = renderer.shadow_info()
        shadow_ok = bool(shadow_ok) and bool(shadow_enabled)

        selected_id = str(selected_block_id).strip()
        if selected_id:
            sel_name = renderer.block_display_name(selected_id)
            sel_line = f"{str(sel_name)} ({str(selected_id)}) Selected\n"
        else:
            sel_line = "Empty Hand Selected\n"

        rd = clamp_render_distance_chunks(int(render_distance_chunks))

        lines: list[str] = []
        lines.append(f"FPS {fps.render_fps:.1f} | SIM {fps.sim_fps:.1f} | T {t_txt}  {vs}")
        lines.append("F4 shadow-debug  F3 HUD  ESC menu  Click capture\n")
        lines.append(f"GPU {gpu_txt} | {mem_line}\nAlloc {self._py.rate_mib_s:.1f} MiB/s")
        lines.append(f"CPU paint {float(paint_ms):.2f} ms\nworld {float(world_perf.cpu_ms):.2f} ms | shadow {float(shadow_perf.cpu_ms):.2f} ms | pick {float(selection_pick_ms):.2f} ms")
        lines.append(f"Draw {int(world_perf.draw_calls)}/{int(shadow_perf.draw_calls)} (W/S) | Inst {int(world_perf.instances)}/{int(shadow_perf.instances)} (W/S)\n")
        lines.append(f"XYZ {px:.2f} {py:.2f} {pz:.2f} |\nBlock {bx} {by} {bz} | Chunk {cx} {cy} {cz} [{rx} {rz}] |")
        lines.append(f"Facing {card} | Yaw {p.yaw_deg:.1f} | Pitch {p.pitch_deg:.1f} |")
        lines.append(f"RenderDist {rd} chunks\n")
        lines.append(f"Mode Creative: {int(bool(creative_mode))} | Flying: {int(bool(flying))} | Inventory: {int(bool(inventory_open))} |")
        lines.append(f"Auto Jump: {int(bool(auto_jump_enabled))} | Auto Sprint: {int(bool(auto_sprint_enabled))} | Reach: {float(reach):.2f} |\n")
        lines.append(str(sel_line))
        lines.append(f"Cloud: {int(bool(cloud_enabled))} | Density: {int(cloud_density)} |\nSeed: {int(cloud_seed)} | Cloud Wireflame: {int(bool(cloud_wire))} |\n")
        lines.append(f"World Wireflame: {int(bool(world_wire))} | Shadow: {int(bool(shadow_ok))} | Size: {int(shadow_size)} | DBG: {int(bool(debug_shadow))} | Sun: {float(sun_az_deg):.0f}/{float(sun_el_deg):.0f}\n")
        lines.append(f"Maiming v{__version__} | Display: {int(fb_w)}x{int(fb_h)} | DPR: {float(dpr):.2f}")

        gl_vendor, gl_rend, gl_ver, _glsl = renderer.gl_info()
        if gl_rend:
            lines.append(str(gl_rend))
        if gl_ver:
            lines.append(f"OpenGL {str(gl_ver)}")
        if gl_vendor:
            lines.append(str(gl_vendor))

        return "\n".join(lines).rstrip()

    def _build_right_text(self, *, session: SessionManager) -> str:
        metrics = self._metrics.snapshot(settings=session.settings)
        recent = float(metrics.recent_window_s)

        lines: list[str] = []
        lines.append("HSpeed blk/s:")
        lines.append(f"Current: {metrics.horiz_speed.current:.3f} | Average: {metrics.horiz_speed.mean:.3f} |")
        lines.append(f"Recent: {recent:.1f}s {metrics.horiz_speed.recent_mean:.3f} |\n")
        lines.append("VSpeed blk/s:")
        lines.append(f"Current: {metrics.vert_speed.current:.3f} | Average: {metrics.vert_speed.mean:.3f} |")
        lines.append(f"Recent: {recent:.1f}s {metrics.vert_speed.recent_mean:.3f} |\n")
        lines.append("JumpInt/s:")
        lines.append(f"Current: {self._fmt_optional(metrics.jump_interval.current)} | Average: {self._fmt_optional(metrics.jump_interval.mean)} |")
        lines.append(f"Recent: {recent:.1f}s {self._fmt_optional(metrics.jump_interval.recent_mean)} |\n")
        lines.append(f"Gravity: {metrics.applied.gravity:.3f} | Walk Speed: {metrics.applied.walk_speed:.3f} |")
        lines.append(f"Sprint Speed: {metrics.applied.sprint_speed:.3f} |")
        lines.append(f"Jump v0: {metrics.applied.jump_v0:.3f} | Auto Jump Cooldown/s: {metrics.applied.auto_jump_cooldown_s:.3f} |")
        return "\n".join(lines).rstrip()

    def build_payload(self, *, session: SessionManager, renderer: GLRenderer, auto_jump_enabled: bool, auto_sprint_enabled: bool, creative_mode: bool, flying: bool, inventory_open: bool, selected_block_id: str, reach: float, sun_az_deg: float, sun_el_deg: float, shadow_enabled: bool, world_wire: bool, cloud_wire: bool, cloud_enabled: bool, cloud_density: int, cloud_seed: int, debug_shadow: bool, fb_w: int, fb_h: int, dpr: float, vsync_on: bool, render_timer_interval_ms: int, sim_hz: float, render_distance_chunks: int, paint_ms: float, selection_pick_ms: float) -> HudPayload:
        _ = float(sim_hz)

        left = self._build_left_text(session=session, renderer=renderer, auto_jump_enabled=bool(auto_jump_enabled), auto_sprint_enabled=bool(auto_sprint_enabled), creative_mode=bool(creative_mode), flying=bool(flying), inventory_open=bool(inventory_open), selected_block_id=str(selected_block_id), reach=float(reach), sun_az_deg=float(sun_az_deg), sun_el_deg=float(sun_el_deg), shadow_enabled=bool(shadow_enabled), world_wire=bool(world_wire), cloud_wire=bool(cloud_wire), cloud_enabled=bool(cloud_enabled), cloud_density=int(cloud_density), cloud_seed=int(cloud_seed), debug_shadow=bool(debug_shadow), fb_w=int(fb_w), fb_h=int(fb_h), dpr=float(dpr), vsync_on=bool(vsync_on), render_timer_interval_ms=int(render_timer_interval_ms), render_distance_chunks=int(render_distance_chunks), paint_ms=float(paint_ms), selection_pick_ms=float(selection_pick_ms))
        right = self._build_right_text(session=session)
        return HudPayload(left_text=str(left), right_text=str(right))