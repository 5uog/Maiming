# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/passes/cloud_pass.py
from __future__ import annotations

import time
import numpy as np

from OpenGL.GL import glEnable, glDisable, glDepthMask, glDepthFunc, glBlendFunc, glBlendEquation, glCullFace, glPolygonMode, glBindVertexArray, glDrawArraysInstanced, GL_DEPTH_TEST, GL_LESS, GL_BLEND, GL_FUNC_ADD, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_CULL_FACE, GL_BACK, GL_FRONT_AND_BACK, GL_LINE, GL_FILL, GL_TRIANGLES

from ludoxel.shared.core.math.vec3 import Vec3
from ludoxel.shared.presentation.opengl.gl.shader_program import ShaderProgram
from ludoxel.shared.presentation.opengl.gl.mesh_buffer import MeshBuffer
from ludoxel.shared.application.rendering.cloud_field import CloudField
from ludoxel.shared.application.rendering.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction
from ludoxel.shared.presentation.opengl.runtime.gl_renderer_params import CloudParams, CameraParams


class CloudPass:

    def __init__(self, clouds: CloudParams, camera: CameraParams) -> None:
        self._cfg = clouds
        self._cam = camera

        self._prog: ShaderProgram | None = None
        self._mesh: MeshBuffer | None = None

        self._field = CloudField(self._cfg)

        self._wireframe = False
        self._enabled = True

        self._density = int(max(0, int(self._cfg.rects_per_cell)))
        self._seed = int(self._cfg.seed)
        self._flow_direction = normalize_cloud_flow_direction(DEFAULT_CLOUD_FLOW_DIRECTION)

        self._motion_paused = False
        self._time_accum = 0.0
        self._last_clock = time.perf_counter()

        self._field.set_density(int(self._density))
        self._field.set_seed(int(self._seed))
        self._field.set_flow_direction(self._flow_direction, t_seconds=0.0)

    def initialize(self, prog: ShaderProgram, mesh: MeshBuffer) -> None:
        self._prog = prog
        self._mesh = mesh
        self._time_accum = 0.0
        self._last_clock = time.perf_counter()
        self._field.set_flow_direction(self._flow_direction, t_seconds=0.0)

    def _advance_clock(self) -> None:
        now = time.perf_counter()
        dt = max(0.0, min(0.25, now - self._last_clock))
        self._last_clock = now

        if not bool(self._motion_paused):
            self._time_accum += float(dt)

    def set_wireframe(self, on: bool) -> None:
        self._wireframe = bool(on)

    def set_enabled(self, on: bool) -> None:
        self._enabled = bool(on)

    def set_density(self, density: int) -> None:
        d = int(max(0, density))
        if d == int(self._density):
            return
        self._density = d
        self._field.set_density(int(self._density))

    def set_seed(self, seed: int) -> None:
        s = int(seed)
        if s == int(self._seed):
            return
        self._seed = s
        self._field.set_seed(int(self._seed))

    def set_flow_direction(self, direction: str) -> None:
        self._advance_clock()
        nxt = normalize_cloud_flow_direction(str(direction))
        if str(nxt) == str(self._flow_direction):
            return
        self._flow_direction = str(nxt)
        self._field.set_flow_direction(str(self._flow_direction), t_seconds=float(self._time_accum))

    def set_motion_paused(self, on: bool) -> None:
        self._advance_clock()
        self._motion_paused = bool(on)

    def draw(self, eye: Vec3, view_proj: np.ndarray, forward: Vec3, fov_deg: float, aspect: float, sun_dir: Vec3) -> None:
        self._advance_clock()

        if not bool(self._enabled):
            return
        if int(self._density) <= 0:
            return
        if self._prog is None or self._mesh is None:
            return

        shift = self._field.shift(float(self._time_accum))

        boxes = self._field.visible_boxes(eye=eye, shift=shift, forward=forward, fov_deg=float(fov_deg), aspect=float(aspect), z_far=float(self._cam.z_far))
        if not boxes:
            return

        data = np.array([[b.center.x, b.center.y, b.center.z, b.size.x, b.size.y, b.size.z, b.alpha_mul] for b in boxes], dtype=np.float32)
        self._mesh.upload_instances(data)
        inst_count = int(data.shape[0])

        glEnable(GL_DEPTH_TEST)
        glDepthMask(True)
        glDepthFunc(GL_LESS)

        glEnable(GL_BLEND)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        if self._wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        self._prog.use()
        self._prog.set_mat4("u_viewProj", view_proj)
        self._prog.set_vec3("u_shift", shift.x, shift.y, shift.z)

        col = self._cfg.color
        self._prog.set_vec3("u_color", float(col.x), float(col.y), float(col.z))
        self._prog.set_float("u_alpha", float(self._cfg.alpha))

        self._prog.set_vec3("u_sunDir", sun_dir.x, sun_dir.y, sun_dir.z)

        glBindVertexArray(self._mesh.vao)
        glDrawArraysInstanced(GL_TRIANGLES, 0, self._mesh.vertex_count, inst_count)
        glBindVertexArray(0)

        if self._wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glDisable(GL_CULL_FACE)
        glDisable(GL_BLEND)
