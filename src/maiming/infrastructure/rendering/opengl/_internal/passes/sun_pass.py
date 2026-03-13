# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/sun_pass.py
from __future__ import annotations
import math

import numpy as np

from OpenGL.GL import glDisable, glEnable, glDepthMask, glBlendFunc, glBlendEquation, glBindVertexArray, glDrawArraysInstanced, GL_DEPTH_TEST, GL_BLEND, GL_FUNC_ADD, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_TRIANGLES

from ......core.math.vec3 import Vec3
from ..gl.shader_program import ShaderProgram
from ...facade.gl_renderer_params import SunParams

class SunPass:
    def __init__(self, cfg: SunParams) -> None:
        self._cfg = cfg
        self._prog: ShaderProgram | None = None

        self._empty_vao: int = 0

    def initialize(self, prog: ShaderProgram, empty_vao: int) -> None:
        self._prog = prog
        self._empty_vao = int(empty_vao)

    def draw(self, eye: Vec3, view_proj: np.ndarray, sun_dir: Vec3) -> None:
        if self._prog is None or int(self._empty_vao) == 0:
            return

        glDisable(GL_DEPTH_TEST)
        glDepthMask(False)

        glEnable(GL_BLEND)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        sun_center, sun_u, sun_v, sun_half = self._sun_quad(eye=eye, d=sun_dir.normalized())

        self._prog.use()
        self._prog.set_mat4("u_viewProj", view_proj)
        self._prog.set_vec3("u_center", sun_center.x, sun_center.y, sun_center.z)
        self._prog.set_vec3("u_u", sun_u.x, sun_u.y, sun_u.z)
        self._prog.set_vec3("u_v", sun_v.x, sun_v.y, sun_v.z)
        self._prog.set_float("u_halfSize", float(sun_half))

        glBindVertexArray(int(self._empty_vao))
        glDrawArraysInstanced(GL_TRIANGLES, 0, 6, 1)
        glBindVertexArray(0)

        glDisable(GL_BLEND)

    def _sun_quad(self, eye: Vec3, d: Vec3) -> tuple[Vec3, Vec3, Vec3, float]:
        up = Vec3(0.0, 1.0, 0.0)

        u = up.cross(d)
        if u.length() <= 1e-6:
            u = Vec3(1.0, 0.0, 0.0).cross(d)
        u = u.normalized()
        v = d.cross(u).normalized()

        sun_dist = float(self._cfg.distance)
        sun_center = eye + d * sun_dist

        half_angle = float(self._cfg.half_angle_deg)
        sun_half = math.tan(math.radians(half_angle)) * sun_dist
        return sun_center, u, v, float(sun_half)