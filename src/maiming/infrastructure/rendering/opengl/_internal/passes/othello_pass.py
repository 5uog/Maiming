# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/othello_pass.py
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import GL_BLEND, GL_CULL_FACE, GL_DEPTH_TEST, GL_LEQUAL, GL_LESS, GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA, GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE_2D, GL_TRIANGLES, glActiveTexture, glBindTexture, glBindVertexArray, glBlendFunc, glDepthFunc, glDepthMask, glDisable, glDrawArraysInstanced, glEnable

from ......core.math.vec3 import Vec3
from ..gl.colored_mesh_buffer import ColoredMeshBuffer
from ..gl.gl_state_guard import GLStateGuard
from ..gl.shader_program import ShaderProgram
from ..scene.othello_scene import build_othello_board_vertices, build_othello_instance_rows, build_othello_piece_vertices
from ...facade.gl_renderer_params import ShadowParams
from ...facade.othello_render_state import OthelloRenderState
from ...facade.render_metrics import PassFrameMetrics
from .shadow_map_pass import ShadowMapInfo

@dataclass
class OthelloPass:
    _world_prog: ShaderProgram | None = None
    _shadow_prog: ShaderProgram | None = None
    _board_mesh: ColoredMeshBuffer | None = None
    _piece_mesh: ColoredMeshBuffer | None = None

    def initialize(self, *, world_prog: ShaderProgram, shadow_prog: ShaderProgram) -> None:
        self._world_prog = world_prog
        self._shadow_prog = shadow_prog
        self._board_mesh = ColoredMeshBuffer.create_transform_color_instanced(build_othello_board_vertices())
        self._piece_mesh = ColoredMeshBuffer.create_transform_color_instanced(build_othello_piece_vertices())

    def destroy(self) -> None:
        if self._board_mesh is not None:
            self._board_mesh.destroy()
        if self._piece_mesh is not None:
            self._piece_mesh.destroy()
        self._board_mesh = None
        self._piece_mesh = None
        self._world_prog = None
        self._shadow_prog = None

    def draw(
        self,
        *,
        render_state: OthelloRenderState | None,
        view_proj: np.ndarray,
        light_view_proj: np.ndarray,
        sun_dir: Vec3,
        debug_shadow: bool,
        shadow_enabled: bool,
        shadow: ShadowParams,
        shadow_info: ShadowMapInfo,
    ) -> PassFrameMetrics:
        if self._world_prog is None or self._board_mesh is None or self._piece_mesh is None or render_state is None or not bool(render_state.enabled):
            return PassFrameMetrics()

        board_rows, highlight_rows, piece_rows = build_othello_instance_rows(render_state)
        if int(board_rows.shape[0]) <= 0 and int(highlight_rows.shape[0]) <= 0 and int(piece_rows.shape[0]) <= 0:
            return PassFrameMetrics()

        draw_calls = 0
        instances = 0

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE), capture_cull_mode=False, capture_polygon_mode=False):
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)
            glDisable(GL_CULL_FACE)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)

            self._world_prog.use()
            self._world_prog.set_mat4("u_viewProj", np.asarray(view_proj, dtype=np.float32))
            self._world_prog.set_mat4("u_lightViewProj", np.asarray(light_view_proj, dtype=np.float32))
            self._world_prog.set_vec3("u_sunDir", float(sun_dir.x), float(sun_dir.y), float(sun_dir.z))

            use_shadow_program = bool(shadow_enabled or debug_shadow)
            shadow_sampling_ok = bool(use_shadow_program and shadow_enabled and shadow_info.ok and int(shadow_info.tex_id) != 0 and int(shadow_info.inst_count) > 0)
            ss = float(max(1, int(shadow_info.size))) if shadow_sampling_ok else 1.0
            self._world_prog.set_int("u_shadowMap", 1)
            self._world_prog.set_int("u_shadowEnabled", 1 if shadow_sampling_ok else 0)
            self._world_prog.set_int("u_debugShadow", 1 if bool(debug_shadow) else 0)
            self._world_prog.set_vec2("u_shadowTexel", 1.0 / ss, 1.0 / ss)
            self._world_prog.set_float("u_shadowDarkMul", float(shadow.dark_mul))
            self._world_prog.set_float("u_shadowBiasMin", float(shadow.bias_min))
            self._world_prog.set_float("u_shadowBiasSlope", float(shadow.bias_slope))

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, int(shadow_info.tex_id) if shadow_sampling_ok else 0)
            glActiveTexture(GL_TEXTURE0)

            if int(board_rows.shape[0]) > 0:
                self._board_mesh.upload_instances(board_rows)
                glDepthMask(True)
                glBindVertexArray(int(self._board_mesh.vao))
                glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._board_mesh.vertex_count), int(board_rows.shape[0]))
                glBindVertexArray(0)
                draw_calls += 1
                instances += int(board_rows.shape[0])

            if int(piece_rows.shape[0]) > 0:
                self._piece_mesh.upload_instances(piece_rows)
                glDepthMask(True)
                glBindVertexArray(int(self._piece_mesh.vao))
                glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._piece_mesh.vertex_count), int(piece_rows.shape[0]))
                glBindVertexArray(0)
                draw_calls += 1
                instances += int(piece_rows.shape[0])

            if int(highlight_rows.shape[0]) > 0:
                self._board_mesh.upload_instances(highlight_rows)
                glDepthMask(False)
                glBindVertexArray(int(self._board_mesh.vao))
                glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._board_mesh.vertex_count), int(highlight_rows.shape[0]))
                glBindVertexArray(0)
                glDepthMask(True)
                draw_calls += 1
                instances += int(highlight_rows.shape[0])

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glActiveTexture(GL_TEXTURE0)

        return PassFrameMetrics(cpu_ms=0.0, draw_calls=int(draw_calls), instances=int(instances), rendered=bool(draw_calls > 0))

    def draw_shadow(self, *, render_state: OthelloRenderState | None, light_view_proj: np.ndarray) -> tuple[int, int]:
        if self._shadow_prog is None or self._piece_mesh is None or render_state is None or not bool(render_state.enabled):
            return (0, 0)

        _board_rows, _highlight_rows, piece_rows = build_othello_instance_rows(render_state)
        if piece_rows.size <= 0 or int(piece_rows.shape[0]) <= 0:
            return (0, 0)

        self._piece_mesh.upload_instances(piece_rows)

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE), capture_cull_mode=False, capture_polygon_mode=False):
            glDisable(GL_BLEND)
            glDisable(GL_CULL_FACE)
            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            self._shadow_prog.use()
            self._shadow_prog.set_mat4("u_lightViewProj", light_view_proj.astype(np.float32, copy=False))

            glBindVertexArray(int(self._piece_mesh.vao))
            glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._piece_mesh.vertex_count), int(piece_rows.shape[0]))
            glBindVertexArray(0)

        return (1, int(piece_rows.shape[0]))