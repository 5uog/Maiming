# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/textured_face_pass.py
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import glActiveTexture, glBindTexture, glBindVertexArray, glDepthFunc, glDepthMask, glDisable, glDrawArraysInstanced, glEnable, GL_BLEND, GL_CULL_FACE, GL_DEPTH_TEST, GL_LESS, GL_TEXTURE0, GL_TEXTURE_2D, GL_TRIANGLES

from ......core.math.vec3 import Vec3
from ..gl.gl_state_guard import GLStateGuard
from ..gl.mesh_buffer import MeshBuffer
from ..gl.shader_program import ShaderProgram

@dataclass
class TexturedFacePass:
    _prog: ShaderProgram | None = None
    _meshes: tuple[MeshBuffer, ...] = ()

    def initialize(self, prog: ShaderProgram) -> None:
        self._prog = prog
        self._meshes = tuple(MeshBuffer.create_quad_transform_instanced(face) for face in range(6))

    def destroy(self) -> None:
        for mesh in self._meshes:
            mesh.destroy()
        self._meshes = ()
        self._prog = None

    def draw(self, *, face_rows: tuple[np.ndarray, ...], view_proj: np.ndarray, tex_id: int, sun_dir: Vec3) -> tuple[int, int]:
        if self._prog is None or len(self._meshes) != 6 or int(tex_id) == 0:
            return (0, 0)

        draw_calls = 0
        instances = 0

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE), capture_cull_mode=False, capture_polygon_mode=False):
            glDisable(GL_BLEND)
            glDisable(GL_CULL_FACE)
            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            self._prog.use()
            self._prog.set_mat4("u_viewProj", view_proj.astype(np.float32, copy=False))
            self._prog.set_int("u_texture", 0)
            self._prog.set_vec3("u_sunDir", float(sun_dir.x), float(sun_dir.y), float(sun_dir.z))

            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, int(tex_id))

            for face_idx, rows in enumerate(face_rows):
                if rows.size <= 0 or int(rows.shape[0]) <= 0:
                    continue
                mesh = self._meshes[int(face_idx)]
                mesh.upload_instances(rows)
                glBindVertexArray(int(mesh.vao))
                glDrawArraysInstanced(GL_TRIANGLES, 0, int(mesh.vertex_count), int(rows.shape[0]))
                glBindVertexArray(0)
                draw_calls += 1
                instances += int(rows.shape[0])

            glBindTexture(GL_TEXTURE_2D, 0)

        return (int(draw_calls), int(instances))