# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from dataclasses import dataclass

from OpenGL.GL import glClearColor, glClear, glViewport, glEnable, glDepthFunc, glDepthMask, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_LESS

from ....core.math import mat4
from ....core.math.vec3 import Vec3
from ....core.math.view_angles import forward_from_yaw_pitch_deg
from ....core.math.transform_matrices import rotate_z_deg_matrix
from ....core.spatial.chunking.chunk_grid import chunk_key
from ..passes.cloud_pass import CloudPass
from ..passes.first_person_arm_pass import FirstPersonArmPass
from ..passes.held_block_pass import HeldBlockPass
from .....features.othello.presentation.opengl.passes.othello_pass import OthelloPass
from ..passes.player_model_pass import PlayerModelPass
from ..passes.shadow_map_pass import ShadowMapPass
from ..passes.sun_pass import SunPass
from ..passes.world_pass import WorldDrawInputs, WorldPass
from ..runtime.light_space import compute_light_view_proj
from ....application.rendering.first_person_geometry import FIRST_PERSON_HAND_NEAR
from ....application.rendering.player_model_pose import build_player_model_pose
from ..runtime.gl_renderer_params import GLRendererParams
from .....features.othello.application.rendering.othello_render_state import OthelloRenderState
from ....application.rendering.player_render_state import PlayerRenderState
from ..runtime.render_metrics import PassFrameMetrics, RendererFrameMetrics
from ..runtime.render_state import RendererRuntimeState
from ..runtime.selection_controller import SelectionController

_FIRST_PERSON_REFERENCE_FOV_DEG = 80.0
_FIRST_PERSON_HIGH_FOV_WEIGHT = 0.20

def _first_person_viewmodel_fov_deg(world_fov_deg: float) -> float:
    fov = float(world_fov_deg)
    if fov <= float(_FIRST_PERSON_REFERENCE_FOV_DEG):
        return fov
    return float(_FIRST_PERSON_REFERENCE_FOV_DEG) + (fov - float(_FIRST_PERSON_REFERENCE_FOV_DEG)) * float(_FIRST_PERSON_HIGH_FOV_WEIGHT)

@dataclass(frozen=True)
class FramePipeline:
    cfg: GLRendererParams
    state: RendererRuntimeState
    shadow_pass: ShadowMapPass
    world_pass: WorldPass
    player_pass: PlayerModelPass
    first_person_arm_pass: FirstPersonArmPass
    held_block_pass: HeldBlockPass
    sun_pass: SunPass
    cloud_pass: CloudPass
    othello_pass: OthelloPass
    selection: SelectionController
    sel_tint_strength: float = 0.55

    def shadow_info(self) -> tuple[bool, int]:
        if not bool(self.state.shadow_enabled):
            return (False, 0)

        info = self.shadow_pass.info()
        ok = bool(self.cfg.shadow.enabled and info.ok and int(info.tex_id) != 0 and int(info.inst_count) > 0)
        return (ok, int(info.size) if ok else 0)

    def render(self, *, w: int, h: int, eye: Vec3, yaw_deg: float, pitch_deg: float, roll_deg: float, fov_deg: float, render_distance_chunks: int, player_state: PlayerRenderState | None, othello_state: OthelloRenderState | None) -> RendererFrameMetrics:
        use_light_space = bool(self.state.shadow_enabled or self.state.debug_shadow)
        if bool(use_light_space):
            shadow_info_pre = self.shadow_pass.info()
            light_vp = compute_light_view_proj(center=eye, sun_dir=self.state.sun_dir, sun=self.cfg.sun, shadow=self.cfg.shadow, shadow_size=int(max(1, int(shadow_info_pre.size))))
        else:
            light_vp = mat4.identity()

        player_pose = build_player_model_pose(player_state)

        shadow_metrics = PassFrameMetrics()
        if bool(self.state.shadow_enabled):
            shadow_metrics = self.shadow_pass.render(light_vp, extra_draw=(lambda vp: (lambda player_result, othello_result: (int(player_result[0]) + int(othello_result[0]), int(player_result[1]) + int(othello_result[1])))(self.player_pass.draw_shadow(pose=player_pose, light_view_proj=vp), self.othello_pass.draw_shadow(render_state=othello_state, light_view_proj=vp))))

        forward = forward_from_yaw_pitch_deg(yaw_deg, pitch_deg)

        view = mat4.look_dir(eye, forward)
        if abs(float(roll_deg)) > 1e-6:
            view = mat4.mul(rotate_z_deg_matrix(float(roll_deg)), view)
        proj = mat4.perspective(fov_deg,(w / max(h, 1)), float(self.cfg.camera.z_near), float(self.cfg.camera.z_far))
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

        player_dc, player_inst = self.player_pass.draw_world(pose=player_pose, view_proj=vp, light_view_proj=light_vp, sun_dir=self.state.sun_dir, debug_shadow=bool(self.state.debug_shadow), shadow_enabled=bool(self.state.shadow_enabled), shadow=self.cfg.shadow, shadow_info=shadow_info)

        world_metrics = PassFrameMetrics(cpu_ms=float(world_metrics.cpu_ms), draw_calls=int(world_metrics.draw_calls + player_dc), instances=int(world_metrics.instances + player_inst), rendered=bool(world_metrics.rendered or (player_dc > 0)))

        othello_metrics = self.othello_pass.draw(render_state=othello_state, view_proj=vp, light_view_proj=light_vp, sun_dir=self.state.sun_dir, debug_shadow=bool(self.state.debug_shadow), shadow_enabled=bool(self.state.shadow_enabled), shadow=self.cfg.shadow, shadow_info=shadow_info)

        world_metrics = PassFrameMetrics(cpu_ms=float(world_metrics.cpu_ms), draw_calls=int(world_metrics.draw_calls + othello_metrics.draw_calls), instances=int(world_metrics.instances + othello_metrics.instances), rendered=bool(world_metrics.rendered or othello_metrics.rendered))

        self.cloud_pass.draw(eye=eye, view_proj=vp, forward=forward, fov_deg=float(fov_deg), aspect=float(w) / max(float(h), 1.0), sun_dir=self.state.sun_dir)

        self.selection.draw(view_proj=vp)

        first_person = None if player_state is None else player_state.first_person
        if first_person is not None and bool(first_person.show_view_model) and (bool(first_person.show_arm) or first_person.visible_block_id is not None):
            glClear(GL_DEPTH_BUFFER_BIT)
            hand_fov_deg = _first_person_viewmodel_fov_deg(float(fov_deg))
            hand_vp = mat4.perspective(hand_fov_deg,(w / max(h, 1)), float(FIRST_PERSON_HAND_NEAR), float(self.cfg.camera.z_far))
            if first_person.visible_block_id is not None:
                self.held_block_pass.draw(first_person=first_person, view_proj=hand_vp, sun_dir=self.state.sun_dir)
            else:
                self.first_person_arm_pass.draw(first_person=first_person, view_proj=hand_vp, sun_dir=self.state.sun_dir)

        return RendererFrameMetrics(world=world_metrics, shadow=shadow_metrics)