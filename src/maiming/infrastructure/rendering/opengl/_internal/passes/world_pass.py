# FILE: src/maiming/infrastructure/rendering/opengl/passes/world_pass.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from OpenGL.GL import (
    glActiveTexture, glBindTexture, glEnable, glDisable, glCullFace, glBindVertexArray, glDrawArraysInstanced,
    glPolygonMode,
    GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE_2D, GL_CULL_FACE, GL_BACK, GL_TRIANGLES,
    GL_FRONT_AND_BACK, GL_LINE,
)

from maiming.core.math.vec3 import Vec3
from ..gl.shader_program import ShaderProgram
from ..gl.mesh_buffer import MeshBuffer
from ..gl.gl_state_guard import GLStateGuard
from ..resources.texture_atlas import TextureAtlas
from ...facade.gl_renderer_params import ShadowParams
from .shadow_map_pass import ShadowMapInfo

@dataclass(frozen=True)
class WorldDrawInputs:
    view_proj: np.ndarray
    light_view_proj: np.ndarray
    sun_dir: Vec3
    debug_shadow: bool

    shadow_enabled: bool
    world_wireframe: bool

    shadow: ShadowParams
    shadow_info: ShadowMapInfo

class WorldPass:
    def __init__(self) -> None:
        self._prog: ShaderProgram | None = None
        self._meshes: list[MeshBuffer] | None = None
        self._atlas: TextureAtlas | None = None

        self._counts: list[int] = [0, 0, 0, 0, 0, 0]
        self._last_revision: int = -1

    def initialize(self, prog: ShaderProgram, meshes: list[MeshBuffer], atlas: TextureAtlas) -> None:
        self._prog = prog
        self._meshes = meshes
        self._atlas = atlas

    def upload_faces(self, world_revision: int, faces: list[np.ndarray]) -> None:
        if self._meshes is None:
            return
        if int(world_revision) == int(self._last_revision):
            return
        self._last_revision = int(world_revision)

        if len(faces) != 6:
            faces = (faces + [np.zeros((0, 12), dtype=np.float32) for _ in range(6)])[:6]

        for fi in range(6):
            data = faces[fi]
            if data.dtype != np.float32:
                data = data.astype(np.float32, copy=False)
            if not data.flags["C_CONTIGUOUS"]:
                data = np.ascontiguousarray(data, dtype=np.float32)

            self._meshes[fi].upload_instances(data)
            self._counts[fi] = int(data.shape[0])

    def draw(self, inp: WorldDrawInputs) -> None:
        if self._prog is None or self._meshes is None or self._atlas is None:
            return

        with GLStateGuard(
            capture_framebuffer=False,
            capture_viewport=False,
            capture_enables=(GL_CULL_FACE,),
            capture_cull_mode=True,
            capture_polygon_mode=True,
        ):
            if bool(inp.world_wireframe):
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

            self._prog.use()
            self._prog.set_mat4("u_viewProj", inp.view_proj)
            self._prog.set_mat4("u_lightViewProj", inp.light_view_proj)
            self._prog.set_vec3("u_sunDir", inp.sun_dir.x, inp.sun_dir.y, inp.sun_dir.z)
            self._prog.set_int("u_atlas", 0)
            self._prog.set_int("u_debugShadow", 1 if bool(inp.debug_shadow) else 0)

            shadow_sampling_ok = bool(
                inp.shadow_enabled
                and inp.shadow_info.ok
                and int(inp.shadow_info.tex_id) != 0
                and int(inp.shadow_info.inst_count) > 0
            )
            self._prog.set_int("u_shadowEnabled", 1 if shadow_sampling_ok else 0)
            self._prog.set_int("u_shadowMap", 1)

            ss = float(max(1, int(inp.shadow_info.size))) if shadow_sampling_ok else 1.0
            self._prog.set_vec2("u_shadowTexel", 1.0 / ss, 1.0 / ss)
            self._prog.set_float("u_shadowDarkMul", float(inp.shadow.dark_mul))
            self._prog.set_float("u_shadowBiasMin", float(inp.shadow.bias_min))
            self._prog.set_float("u_shadowBiasSlope", float(inp.shadow.bias_slope))

            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, int(self._atlas.tex_id))

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, int(inp.shadow_info.tex_id) if shadow_sampling_ok else 0)

            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)

            for fi, (mesh, cnt) in enumerate(zip(self._meshes, self._counts)):
                if int(cnt) <= 0:
                    continue
                self._prog.set_int("u_face", int(fi))
                glBindVertexArray(mesh.vao)
                glDrawArraysInstanced(GL_TRIANGLES, 0, mesh.vertex_count, int(cnt))
                glBindVertexArray(0)

            glDisable(GL_CULL_FACE)

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)