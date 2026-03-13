# FILE: src/maiming/infrastructure/rendering/opengl/_internal/pipeline/frame_pipeline.py
from __future__ import annotations
import math
from dataclasses import dataclass

from OpenGL.GL import glClearColor, glClear, glViewport, glEnable, glDepthFunc, glDepthMask, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_LESS

from ......core.math import mat4
from ......core.math.vec3 import Vec3
from ......core.math.view_angles import forward_from_yaw_pitch_deg
from ......domain.world.chunking import chunk_key
from ..passes.cloud_pass import CloudPass
from ..passes.shadow_map_pass import ShadowMapPass
from ..passes.sun_pass import SunPass
from ..passes.world_pass import WorldDrawInputs, WorldPass
from ..pipeline.light_space import compute_light_view_proj
from ...facade.gl_renderer_params import GLRendererParams
from ...facade.render_metrics import PassFrameMetrics, RendererFrameMetrics
from ...facade.render_state import RendererRuntimeState
from ...facade.selection_controller import SelectionController

@dataclass(frozen=True)
class FramePipeline:
    cfg: GLRendererParams
    state: RendererRuntimeState
    shadow_pass: ShadowMapPass
    world_pass: WorldPass
    sun_pass: SunPass
    cloud_pass: CloudPass
    selection: SelectionController
    sel_tint_strength: float = 0.55

    def shadow_info(self) -> tuple[bool, int]:
        if not bool(self.state.shadow_enabled):
            return (False, 0)

        info = self.shadow_pass.info()
        ok = bool(self.cfg.shadow.enabled and info.ok and int(info.tex_id) != 0 and int(info.inst_count) > 0)
        return (ok, int(info.size) if ok else 0)

    def render(self, *, w: int, h: int, eye: Vec3, yaw_deg: float, pitch_deg: float, fov_deg: float, render_distance_chunks: int) -> RendererFrameMetrics:
        shadow_info_pre = self.shadow_pass.info()
        light_vp = compute_light_view_proj(center=eye, sun_dir=self.state.sun_dir, sun=self.cfg.sun, shadow=self.cfg.shadow, shadow_size=int(max(1, int(shadow_info_pre.size))))

        shadow_metrics = PassFrameMetrics()
        if bool(self.state.shadow_enabled):
            shadow_metrics = self.shadow_pass.render(light_vp)

        forward = forward_from_yaw_pitch_deg(yaw_deg, pitch_deg)

        view = mat4.look_dir(eye, forward)
        proj = mat4.perspective(fov_deg, (w / max(h, 1)), float(self.cfg.camera.z_near), float(self.cfg.camera.z_far))
        vp = mat4.mul(proj, view)

        glViewport(0, 0, w, h)
        cc = self.cfg.sky.clear_color
        glClearColor(float(cc.x), float(cc.y), float(cc.z), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.sun_pass.draw(eye=eye, view_proj=vp, sun_dir=self.state.sun_dir)

        glEnable(GL_DEPTH_TEST)
        glDepthMask(True)
        glDepthFunc(GL_LESS)

        shadow_info = self.shadow_pass.info()

        bx = int(math.floor(float(eye.x)))
        by = int(math.floor(float(eye.y)))
        bz = int(math.floor(float(eye.z)))
        cam_ck = chunk_key(bx, by, bz)

        sel_mode, sx, sy, sz = self.selection.world_inputs()

        world_metrics = self.world_pass.draw(WorldDrawInputs(view_proj=vp, light_view_proj=light_vp, sun_dir=self.state.sun_dir, debug_shadow=bool(self.state.debug_shadow), shadow_enabled=bool(self.state.shadow_enabled), world_wireframe=bool(self.state.world_wireframe), shadow=self.cfg.shadow, shadow_info=shadow_info, camera_chunk=cam_ck, render_distance_chunks=int(render_distance_chunks), sel_mode=int(sel_mode), sel_x=int(sx), sel_y=int(sy), sel_z=int(sz), sel_tint=float(self.sel_tint_strength)))

        self.cloud_pass.draw(eye=eye, view_proj=vp, forward=forward, fov_deg=float(fov_deg), aspect=float(w) / max(float(h), 1.0), sun_dir=self.state.sun_dir)

        self.selection.draw(view_proj=vp)
        return RendererFrameMetrics(world=world_metrics, shadow=shadow_metrics)