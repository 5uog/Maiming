# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/world_pass.py
from __future__ import annotations
import time
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import glActiveTexture, glBindTexture, glEnable, glDisable, glCullFace, glPolygonMode, GL_TEXTURE0, GL_TEXTURE1, GL_TEXTURE_2D, GL_CULL_FACE, GL_BACK, GL_FRONT_AND_BACK, GL_LINE

from ......core.math.vec3 import Vec3
from ......domain.world.chunking import ChunkKey
from ..gl.shader_program import ShaderProgram
from ..gl.gl_state_guard import GLStateGuard
from ..resources.texture_atlas import TextureAtlas
from ..scene.chunk_selection import select_visible_chunks, within_render_distance
from ...facade.gl_renderer_params import ShadowParams
from ...facade.render_metrics import PassFrameMetrics
from .aggregated_face_batch import AggregatedFaceBatch
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

    camera_chunk: ChunkKey
    render_distance_chunks: int

    sel_mode: int
    sel_x: int
    sel_y: int
    sel_z: int
    sel_tint: float

class WorldPass:
    def __init__(self) -> None:
        self._prog: ShaderProgram | None = None
        self._atlas: TextureAtlas | None = None
        self._batch = AggregatedFaceBatch()
        self._last_metrics = PassFrameMetrics()

    def initialize(self, prog: ShaderProgram, atlas: TextureAtlas) -> None:
        self._prog = prog
        self._atlas = atlas
        self._batch.initialize()

    def destroy(self) -> None:
        self._batch.destroy()
        self._prog = None
        self._atlas = None
        self._last_metrics = PassFrameMetrics()

    def remove_chunk(self, chunk_key: ChunkKey) -> None:
        self._batch.remove_chunk(chunk_key)

    def evict_except(self, keep: set[ChunkKey]) -> None:
        self._batch.evict_except(keep)

    def upload_chunk(self, *, chunk_key: ChunkKey, world_revision: int, faces: list[np.ndarray]) -> None:
        self._batch.set_chunk_faces(chunk_key=chunk_key, world_revision=int(world_revision), faces=faces)

    def draw(self, inp: WorldDrawInputs) -> PassFrameMetrics:
        t0 = time.perf_counter()

        if self._prog is None or self._atlas is None:
            self._last_metrics = PassFrameMetrics()
            return self._last_metrics

        self._batch.prepare()

        rd = int(max(2, min(16, int(inp.render_distance_chunks))))
        cam = inp.camera_chunk
        view_proj = inp.view_proj.astype(np.float32, copy=False)

        visible_chunks = select_visible_chunks(self._batch.chunk_keys(), view_proj, predicate=lambda ck: within_render_distance(ck, cam, rd))

        commands = self._batch.build_commands(visible_chunks)
        if not any(int(cmd.shape[0]) > 0 for cmd in commands):
            self._last_metrics = PassFrameMetrics(cpu_ms=float((time.perf_counter() - t0) * 1000.0), draw_calls=0, instances=0, rendered=False)
            return self._last_metrics

        draw_calls = 0
        instances = 0

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_CULL_FACE,), capture_cull_mode=True, capture_polygon_mode=True):
            if bool(inp.world_wireframe):
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

            self._prog.use()
            self._prog.set_mat4("u_viewProj", view_proj)
            self._prog.set_mat4("u_lightViewProj", inp.light_view_proj)
            self._prog.set_vec3("u_sunDir", inp.sun_dir.x, inp.sun_dir.y, inp.sun_dir.z)
            self._prog.set_int("u_atlas", 0)
            self._prog.set_int("u_debugShadow", 1 if bool(inp.debug_shadow) else 0)

            shadow_sampling_ok = bool(inp.shadow_enabled and inp.shadow_info.ok and int(inp.shadow_info.tex_id) != 0 and int(inp.shadow_info.inst_count) > 0)
            self._prog.set_int("u_shadowEnabled", 1 if shadow_sampling_ok else 0)
            self._prog.set_int("u_shadowMap", 1)

            ss = float(max(1, int(inp.shadow_info.size))) if shadow_sampling_ok else 1.0
            self._prog.set_vec2("u_shadowTexel", 1.0 / ss, 1.0 / ss)
            self._prog.set_float("u_shadowDarkMul", float(inp.shadow.dark_mul))
            self._prog.set_float("u_shadowBiasMin", float(inp.shadow.bias_min))
            self._prog.set_float("u_shadowBiasSlope", float(inp.shadow.bias_slope))

            self._prog.set_int("u_selMode", int(inp.sel_mode))
            self._prog.set_ivec3("u_selBlock", int(inp.sel_x), int(inp.sel_y), int(inp.sel_z))
            self._prog.set_float("u_selTint", float(inp.sel_tint))

            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, int(self._atlas.tex_id))

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, int(inp.shadow_info.tex_id) if shadow_sampling_ok else 0)

            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)

            draw_calls, instances = self._batch.draw(commands, before_face_draw=lambda fi: self._prog.set_int("u_face", int(fi)))

            glDisable(GL_CULL_FACE)

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)

        self._last_metrics = PassFrameMetrics(cpu_ms=float((time.perf_counter() - t0) * 1000.0), draw_calls=int(draw_calls), instances=int(instances), rendered=bool(draw_calls > 0))
        return self._last_metrics