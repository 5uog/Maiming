# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/shadow_map_pass.py
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import (
    glGenFramebuffers,
    glDeleteFramebuffers,
    glBindFramebuffer,
    glCheckFramebufferStatus,
    glGenTextures,
    glDeleteTextures,
    glBindTexture,
    glTexImage2D,
    glTexParameteri,
    glTexParameterfv,
    glFramebufferTexture2D,
    glDrawBuffer,
    glReadBuffer,
    glViewport,
    glClear,
    glEnable,
    glDisable,
    glDepthMask,
    glDepthFunc,
    glPolygonOffset,
    GL_FRAMEBUFFER,
    GL_FRAMEBUFFER_COMPLETE,
    GL_DEPTH_ATTACHMENT,
    GL_TEXTURE_2D,
    GL_DEPTH_COMPONENT24,
    GL_DEPTH_COMPONENT,
    GL_UNSIGNED_INT,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_MAG_FILTER,
    GL_LINEAR,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_CLAMP_TO_BORDER,
    GL_TEXTURE_BORDER_COLOR,
    GL_TEXTURE_COMPARE_MODE,
    GL_TEXTURE_COMPARE_FUNC,
    GL_COMPARE_REF_TO_TEXTURE,
    GL_LEQUAL,
    GL_NONE,
    GL_BLEND,
    GL_DEPTH_TEST,
    GL_LESS,
    GL_DEPTH_BUFFER_BIT,
    GL_CULL_FACE,
    GL_POLYGON_OFFSET_FILL,
)

from ..gl.shader_program import ShaderProgram
from ..gl.gl_state_guard import GLStateGuard
from ...facade.gl_renderer_params import ShadowParams
from ...facade.render_metrics import PassFrameMetrics
from .aggregated_face_batch import AggregatedFaceBatch
from maiming.domain.world.chunking import ChunkKey, chunk_bounds

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

        self._fbo: int = 0
        self._tex: int = 0
        self._size: int = int(cfg.size)
        self._ok: bool = False

        self._batch = AggregatedFaceBatch()

        self._last_vp_rendered: np.ndarray | None = None
        self._dirty: bool = True
        self._last_metrics = PassFrameMetrics()

    def initialize(self, prog: ShaderProgram, size: int) -> None:
        self._prog = prog
        self._create_shadow_map(size)
        self._batch.initialize()

    def destroy(self) -> None:
        self._batch.destroy()
        self._destroy_shadow_map()
        self._prog = None
        self._last_vp_rendered = None
        self._dirty = True
        self._last_metrics = PassFrameMetrics()

    def info(self) -> ShadowMapInfo:
        return ShadowMapInfo(
            ok=bool(self._ok),
            size=int(self._size),
            tex_id=int(self._tex),
            inst_count=int(self._batch.total_instances()),
        )

    def remove_chunk(self, chunk_key: ChunkKey) -> None:
        self._batch.remove_chunk(chunk_key)
        self._dirty = True

    def evict_except(self, keep: set[ChunkKey]) -> None:
        self._batch.evict_except(keep)
        self._dirty = True

    def set_chunk_faces(self, *, chunk_key: ChunkKey, world_revision: int, faces: list[np.ndarray]) -> None:
        self._batch.set_chunk_faces(
            chunk_key=chunk_key,
            world_revision=int(world_revision),
            faces=faces,
        )
        self._dirty = True

    def should_render(self, light_vp: np.ndarray) -> bool:
        if int(self._batch.total_instances()) <= 0:
            return False
        if bool(self._dirty):
            return True
        if self._last_vp_rendered is None:
            return True

        a = light_vp.astype(np.float32, copy=False)
        b = self._last_vp_rendered.astype(np.float32, copy=False)

        if a.shape != b.shape:
            return True

        return not bool(np.array_equal(a, b))

    @staticmethod
    def _chunk_intersects_light_volume(chunk_key: ChunkKey, light_vp: np.ndarray) -> bool:
        x0, x1, y0, y1, z0, z1 = chunk_bounds(chunk_key)

        corners = np.asarray(
            [
                [float(x0), float(y0), float(z0), 1.0],
                [float(x1), float(y0), float(z0), 1.0],
                [float(x0), float(y1), float(z0), 1.0],
                [float(x1), float(y1), float(z0), 1.0],
                [float(x0), float(y0), float(z1), 1.0],
                [float(x1), float(y0), float(z1), 1.0],
                [float(x0), float(y1), float(z1), 1.0],
                [float(x1), float(y1), float(z1), 1.0],
            ],
            dtype=np.float32,
        )

        clip = (light_vp @ corners.T).T
        xs = clip[:, 0]
        ys = clip[:, 1]
        zs = clip[:, 2]
        ws = clip[:, 3]

        if bool(np.all(xs < (-ws))):
            return False
        if bool(np.all(xs > ws)):
            return False
        if bool(np.all(ys < (-ws))):
            return False
        if bool(np.all(ys > ws)):
            return False
        if bool(np.all(zs < (-ws))):
            return False
        if bool(np.all(zs > ws)):
            return False

        return True

    def render(self, light_vp: np.ndarray) -> PassFrameMetrics:
        t0 = time.perf_counter()

        if self._prog is None:
            self._last_metrics = PassFrameMetrics()
            return self._last_metrics
        if not bool(self._cfg.enabled):
            self._last_metrics = PassFrameMetrics()
            return self._last_metrics
        if not bool(self._ok) or int(self._fbo) == 0 or int(self._tex) == 0:
            self._last_metrics = PassFrameMetrics()
            return self._last_metrics
        if int(self._batch.total_instances()) <= 0:
            self._last_metrics = PassFrameMetrics()
            return self._last_metrics

        self._batch.prepare()

        s = int(self._size)
        vp = light_vp.astype(np.float32, copy=False)

        visible_chunks: list[ChunkKey] = []
        for ck in self._batch.chunk_keys():
            if not self._chunk_intersects_light_volume(ck, vp):
                continue
            visible_chunks.append(ck)

        commands = self._batch.build_commands(visible_chunks)

        draw_calls = 0
        instances = 0

        with GLStateGuard(
            capture_framebuffer=True,
            capture_viewport=True,
            capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE, GL_POLYGON_OFFSET_FILL),
            capture_cull_mode=False,
            capture_polygon_mode=False,
        ):
            glBindFramebuffer(GL_FRAMEBUFFER, int(self._fbo))
            glViewport(0, 0, s, s)

            glDisable(GL_BLEND)
            glDisable(GL_CULL_FACE)

            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            glClear(GL_DEPTH_BUFFER_BIT)

            glEnable(GL_POLYGON_OFFSET_FILL)
            glPolygonOffset(float(self._cfg.poly_offset_factor), float(self._cfg.poly_offset_units))

            self._prog.use()
            self._prog.set_mat4("u_lightViewProj", vp)

            draw_calls, instances = self._batch.draw(
                commands,
                before_face_draw=lambda fi: self._prog.set_int("u_face", int(fi)),
            )

            glDisable(GL_POLYGON_OFFSET_FILL)

        self._last_vp_rendered = vp.copy()
        self._dirty = False
        self._last_metrics = PassFrameMetrics(
            cpu_ms=float((time.perf_counter() - t0) * 1000.0),
            draw_calls=int(draw_calls),
            instances=int(instances),
            rendered=True,
        )
        return self._last_metrics

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