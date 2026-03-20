# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/passes/player_model_pass.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from OpenGL.GL import glActiveTexture, glBindTexture, glBindVertexArray, glDrawArraysInstanced, glEnable, glDisable, glDepthFunc, glDepthMask, GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE_2D, GL_DEPTH_TEST, GL_LESS, GL_BLEND, GL_CULL_FACE, GL_TRIANGLES

from ....core.math.vec3 import Vec3
from ..gl.gl_state_guard import GLStateGuard
from ..gl.mesh_buffer import MeshBuffer
from ..gl.shader_program import ShaderProgram
from ....application.rendering.player_model_pose import PlayerModelPose
from ..runtime.gl_renderer_params import ShadowParams
from ..runtime.render_metrics import PassFrameMetrics
from .shadow_map_pass import ShadowMapInfo


@dataclass
class PlayerModelPass:
    _world_prog: ShaderProgram | None = None
    _world_no_shadow_prog: ShaderProgram | None = None
    _shadow_prog: ShaderProgram | None = None
    _mesh: MeshBuffer | None = None
    _color: Vec3 = Vec3(0.93, 0.80, 0.72)

    def initialize(self, *, world_prog: ShaderProgram, no_shadow_prog: ShaderProgram, shadow_prog: ShaderProgram, mesh: MeshBuffer) -> None:
        self._world_prog = world_prog
        self._world_no_shadow_prog = no_shadow_prog
        self._shadow_prog = shadow_prog
        self._mesh = mesh

    def destroy(self) -> None:
        self._world_prog = None
        self._world_no_shadow_prog = None
        self._shadow_prog = None
        self._mesh = None

    def draw_world(self, *, pose: PlayerModelPose, view_proj: np.ndarray, light_view_proj: np.ndarray, sun_dir: Vec3, debug_shadow: bool, shadow_enabled: bool, shadow: ShadowParams, shadow_info: ShadowMapInfo) -> tuple[int, int]:
        if self._world_prog is None or self._world_no_shadow_prog is None or self._mesh is None:
            return (0, 0)

        rows = pose.world_rows
        if rows.size <= 0 or int(rows.shape[0]) <= 0:
            return (0, 0)

        self._mesh.upload_instances(rows)

        use_shadow_program = bool(shadow_enabled or debug_shadow)
        prog = self._world_prog if bool(use_shadow_program) else self._world_no_shadow_prog
        shadow_sampling_ok = bool(use_shadow_program and shadow_enabled and shadow_info.ok and int(shadow_info.tex_id) != 0 and int(shadow_info.inst_count) > 0)
        ss = float(max(1, int(shadow_info.size))) if shadow_sampling_ok else 1.0

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE), capture_cull_mode=False, capture_polygon_mode=False):
            glDisable(GL_BLEND)
            glDisable(GL_CULL_FACE)

            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            prog.use()
            prog.set_mat4("u_viewProj", view_proj.astype(np.float32, copy=False))
            prog.set_mat4("u_lightViewProj", light_view_proj.astype(np.float32, copy=False))
            prog.set_vec3("u_sunDir", float(sun_dir.x), float(sun_dir.y), float(sun_dir.z))
            prog.set_vec3("u_color", float(self._color.x), float(self._color.y), float(self._color.z))

            if bool(use_shadow_program):
                prog.set_int("u_shadowMap", 1)
                prog.set_int("u_shadowEnabled", 1 if shadow_sampling_ok else 0)
                prog.set_int("u_debugShadow", 1 if bool(debug_shadow) else 0)
                prog.set_vec2("u_shadowTexel", 1.0 / ss, 1.0 / ss)
                prog.set_float("u_shadowDarkMul", float(shadow.dark_mul))
                prog.set_float("u_shadowBiasMin", float(shadow.bias_min))
                prog.set_float("u_shadowBiasSlope", float(shadow.bias_slope))

                glActiveTexture(GL_TEXTURE1)
                glBindTexture(GL_TEXTURE_2D, int(shadow_info.tex_id) if shadow_sampling_ok else 0)

            glBindVertexArray(int(self._mesh.vao))
            glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._mesh.vertex_count), int(rows.shape[0]))
            glBindVertexArray(0)

            if bool(use_shadow_program):
                glActiveTexture(GL_TEXTURE1)
                glBindTexture(GL_TEXTURE_2D, 0)
                glActiveTexture(GL_TEXTURE0)

        return (1, int(rows.shape[0]))

    def draw_shadow(self, *, pose: PlayerModelPose, light_view_proj: np.ndarray) -> tuple[int, int]:
        if self._shadow_prog is None or self._mesh is None:
            return (0, 0)

        rows = pose.shadow_rows
        if rows.size <= 0 or int(rows.shape[0]) <= 0:
            return (0, 0)

        self._mesh.upload_instances(rows)

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE), capture_cull_mode=False, capture_polygon_mode=False):
            glDisable(GL_BLEND)
            glDisable(GL_CULL_FACE)

            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            self._shadow_prog.use()
            self._shadow_prog.set_mat4("u_lightViewProj", light_view_proj.astype(np.float32, copy=False))

            glBindVertexArray(int(self._mesh.vao))
            glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._mesh.vertex_count), int(rows.shape[0]))
            glBindVertexArray(0)

        return (1, int(rows.shape[0]))

    def world_metrics(self, *, pose: PlayerModelPose, view_proj: np.ndarray, light_view_proj: np.ndarray, sun_dir: Vec3, debug_shadow: bool, shadow_enabled: bool, shadow: ShadowParams, shadow_info: ShadowMapInfo) -> PassFrameMetrics:
        dc, inst = self.draw_world(pose=pose, view_proj=view_proj, light_view_proj=light_view_proj, sun_dir=sun_dir, debug_shadow=bool(debug_shadow), shadow_enabled=bool(shadow_enabled), shadow=shadow, shadow_info=shadow_info)
        return PassFrameMetrics(cpu_ms=0.0, draw_calls=int(dc), instances=int(inst), rendered=bool(dc > 0))
