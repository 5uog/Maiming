# FILE: src/maiming/infrastructure/rendering/opengl/passes/shadow_map_pass.py
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from OpenGL.GL import (
    glGenFramebuffers, glDeleteFramebuffers, glBindFramebuffer, glCheckFramebufferStatus, glGenTextures,
    glDeleteTextures, glBindTexture, glTexImage2D, glTexParameteri, glTexParameterfv, glFramebufferTexture2D,
    glDrawBuffer, glReadBuffer, glViewport, glClear, glEnable, glDisable, glDepthMask, glDepthFunc, glCullFace,
    glPolygonOffset, glBindVertexArray, glDrawArraysInstanced,
    GL_FRAMEBUFFER, GL_FRAMEBUFFER_COMPLETE, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, GL_DEPTH_COMPONENT24,
    GL_DEPTH_COMPONENT, GL_UNSIGNED_INT, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_LINEAR,
    GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER, GL_TEXTURE_BORDER_COLOR, GL_TEXTURE_COMPARE_MODE,
    GL_TEXTURE_COMPARE_FUNC, GL_COMPARE_REF_TO_TEXTURE, GL_LEQUAL, GL_NONE, GL_BLEND, GL_DEPTH_TEST, GL_LESS,
    GL_DEPTH_BUFFER_BIT, GL_CULL_FACE, GL_BACK, GL_FRONT, GL_POLYGON_OFFSET_FILL, GL_TRIANGLES,
)

from ..gl.shader_program import ShaderProgram
from ..gl.mesh_buffer import MeshBuffer
from ..gl.gl_state_guard import GLStateGuard
from ...facade.gl_renderer_params import ShadowParams
from ..scene.instance_types import ShadowCasterGPU

@dataclass
class ShadowMapInfo:
    ok: bool
    size: int
    tex_id: int
    inst_count: int

class ShadowMapPass:
    def __init__(self, cfg: ShadowParams) -> None:
        self._cfg = cfg

        self._prog: ShaderProgram | None = None
        self._mesh: MeshBuffer | None = None

        self._fbo: int = 0
        self._tex: int = 0
        self._size: int = int(cfg.size)
        self._ok: bool = False

        self._inst_count: int = 0
        self._last_vp_rendered: np.ndarray | None = None
        self._last_revision: int = -1
        self._dirty: bool = True

    def initialize(self, prog: ShaderProgram, cube_mesh: MeshBuffer, size: int) -> None:
        self._prog = prog
        self._mesh = cube_mesh
        self._create_shadow_map(size)

    def destroy(self) -> None:
        self._destroy_shadow_map()
        self._prog = None
        self._mesh = None
        self._last_vp_rendered = None
        self._last_revision = -1
        self._dirty = True

    def info(self) -> ShadowMapInfo:
        return ShadowMapInfo(
            ok=bool(self._ok),
            size=int(self._size),
            tex_id=int(self._tex),
            inst_count=int(self._inst_count),
        )

    def set_casters(self, world_revision: int, casters: list[ShadowCasterGPU]) -> None:
        if self._mesh is None:
            return

        if int(world_revision) == int(self._last_revision):
            return
        self._last_revision = int(world_revision)

        if not casters:
            data = np.zeros((0, 7), dtype=np.float32)
            self._mesh.upload_instances(data)
            self._inst_count = 0
            self._dirty = False
            self._last_vp_rendered = None
            return

        data = np.array(
            [[c.cx, c.cy, c.cz, c.sx, c.sy, c.sz, 0.0] for c in casters],
            dtype=np.float32,
        )
        self._mesh.upload_instances(data)
        self._inst_count = int(data.shape[0])
        self._dirty = True

    def should_render(self, light_vp: np.ndarray) -> bool:
        if int(self._inst_count) <= 0:
            return False
        if bool(self._dirty):
            return True
        if self._last_vp_rendered is None:
            return True

        a = light_vp.astype(np.float32)
        b = self._last_vp_rendered.astype(np.float32)
        if a.shape != b.shape:
            return True

        diff = float(np.max(np.abs(a - b)))
        return diff > 1e-6

    def render(self, light_vp: np.ndarray) -> None:
        if self._prog is None or self._mesh is None:
            return
        if not bool(self._cfg.enabled):
            return
        if not bool(self._ok) or int(self._fbo) == 0 or int(self._tex) == 0:
            return
        if int(self._inst_count) <= 0:
            return

        s = int(self._size)

        with GLStateGuard(
            capture_framebuffer=True,
            capture_viewport=True,
            capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE, GL_POLYGON_OFFSET_FILL),
            capture_cull_mode=True,
            capture_polygon_mode=False,
        ):
            glBindFramebuffer(GL_FRAMEBUFFER, int(self._fbo))
            glViewport(0, 0, s, s)

            glDisable(GL_BLEND)

            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            glClear(GL_DEPTH_BUFFER_BIT)

            glEnable(GL_CULL_FACE)
            glCullFace(GL_FRONT if bool(self._cfg.cull_front) else GL_BACK)

            glEnable(GL_POLYGON_OFFSET_FILL)
            glPolygonOffset(float(self._cfg.poly_offset_factor), float(self._cfg.poly_offset_units))

            self._prog.use()
            self._prog.set_mat4("u_lightViewProj", light_vp)

            glBindVertexArray(self._mesh.vao)
            glDrawArraysInstanced(GL_TRIANGLES, 0, self._mesh.vertex_count, int(self._inst_count))
            glBindVertexArray(0)

            glDisable(GL_POLYGON_OFFSET_FILL)
            glDisable(GL_CULL_FACE)

        self._last_vp_rendered = light_vp.copy()
        self._dirty = False

    def _destroy_shadow_map(self) -> None:
        if int(self._tex) != 0:
            glDeleteTextures(1, [int(self._tex)])
            self._tex = 0
        if int(self._fbo) != 0:
            glDeleteFramebuffers(1, [int(self._fbo)])
            self._fbo = 0
        self._ok = False
        self._last_vp_rendered = None
        self._dirty = True

    def _create_shadow_map(self, size: int) -> None:
        size_i = int(max(64, min(8192, int(size))))
        self._size = size_i

        self._destroy_shadow_map()

        tex = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, tex)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_DEPTH_COMPONENT24,
            size_i,
            size_i,
            0,
            GL_DEPTH_COMPONENT,
            GL_UNSIGNED_INT,
            None,
        )

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, [1.0, 1.0, 1.0, 1.0])

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL)

        glBindTexture(GL_TEXTURE_2D, 0)

        fbo = int(glGenFramebuffers(1))
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, tex, 0)

        glDrawBuffer(GL_NONE)
        glReadBuffer(GL_NONE)

        status = int(glCheckFramebufferStatus(GL_FRAMEBUFFER))
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        if status != int(GL_FRAMEBUFFER_COMPLETE):
            glDeleteTextures(1, [int(tex)])
            glDeleteFramebuffers(1, [int(fbo)])
            self._tex = 0
            self._fbo = 0
            self._ok = False
            self._dirty = True
            return

        self._tex = tex
        self._fbo = fbo
        self._ok = True
        self._dirty = True