# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/world_pass.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np

from OpenGL.GL import (
    glActiveTexture,
    glBindTexture,
    glEnable,
    glDisable,
    glCullFace,
    glBindVertexArray,
    glDrawArraysInstanced,
    glPolygonMode,
    GL_TEXTURE0,
    GL_TEXTURE1,
    GL_TEXTURE_2D,
    GL_CULL_FACE,
    GL_BACK,
    GL_TRIANGLES,
    GL_FRONT_AND_BACK,
    GL_LINE,
)

from maiming.core.math.vec3 import Vec3
from ..gl.shader_program import ShaderProgram
from ..gl.mesh_buffer import MeshBuffer
from ..gl.gl_state_guard import GLStateGuard
from ..resources.texture_atlas import TextureAtlas
from ...facade.gl_renderer_params import ShadowParams
from .shadow_map_pass import ShadowMapInfo
from maiming.domain.world.chunking import ChunkKey, chunk_bounds

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


@dataclass
class _ChunkFaces:
    meshes: list[MeshBuffer]
    counts: list[int]
    last_rev: int


class WorldPass:
    def __init__(self) -> None:
        self._prog: ShaderProgram | None = None
        self._atlas: TextureAtlas | None = None
        self._chunks: Dict[ChunkKey, _ChunkFaces] = {}

    def initialize(self, prog: ShaderProgram, atlas: TextureAtlas) -> None:
        self._prog = prog
        self._atlas = atlas

    def destroy(self) -> None:
        for ch in self._chunks.values():
            for m in ch.meshes:
                m.destroy()
        self._chunks.clear()
        self._prog = None
        self._atlas = None

    def _ensure_chunk(self, k: ChunkKey) -> _ChunkFaces:
        ch = self._chunks.get(k)
        if ch is not None:
            return ch

        meshes = [MeshBuffer.create_quad_instanced(i) for i in range(6)]
        counts = [0, 0, 0, 0, 0, 0]
        ch = _ChunkFaces(meshes=meshes, counts=counts, last_rev=-1)
        self._chunks[k] = ch
        return ch

    def remove_chunk(self, chunk_key: ChunkKey) -> None:
        ck = (int(chunk_key[0]), int(chunk_key[1]), int(chunk_key[2]))
        ch = self._chunks.pop(ck, None)
        if ch is None:
            return
        for mesh in ch.meshes:
            mesh.destroy()

    def evict_except(self, keep: set[ChunkKey]) -> None:
        keep_n = {(int(k[0]), int(k[1]), int(k[2])) for k in keep}
        doomed = [ck for ck in self._chunks.keys() if ck not in keep_n]
        for ck in doomed:
            self.remove_chunk(ck)

    def upload_chunk(self, *, chunk_key: ChunkKey, world_revision: int, faces: list[np.ndarray]) -> None:
        if len(faces) != 6:
            return
        ch = self._ensure_chunk(chunk_key)
        if int(world_revision) == int(ch.last_rev):
            return
        ch.last_rev = int(world_revision)

        for fi in range(6):
            data = faces[fi]
            if data.dtype != np.float32:
                data = data.astype(np.float32, copy=False)
            if not data.flags["C_CONTIGUOUS"]:
                data = np.ascontiguousarray(data, dtype=np.float32)
            ch.meshes[fi].upload_instances(data)
            ch.counts[fi] = int(data.shape[0])

    @staticmethod
    def _within_render_distance(ck: ChunkKey, cam: ChunkKey, rd: int) -> bool:
        dx = abs(int(ck[0]) - int(cam[0]))
        dz = abs(int(ck[2]) - int(cam[2]))
        dy = abs(int(ck[1]) - int(cam[1]))
        return (dx <= int(rd)) and (dz <= int(rd)) and (dy <= 1)

    @staticmethod
    def _chunk_intersects_view_volume(chunk_key: ChunkKey, view_proj: np.ndarray) -> bool:
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

        clip = (view_proj @ corners.T).T
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

    def draw(self, inp: WorldDrawInputs) -> None:
        if self._prog is None or self._atlas is None:
            return

        rd = int(max(2, min(16, int(inp.render_distance_chunks))))
        cam = inp.camera_chunk
        view_proj = inp.view_proj.astype(np.float32, copy=False)

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
            self._prog.set_mat4("u_viewProj", view_proj)
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

            self._prog.set_int("u_selMode", int(inp.sel_mode))
            self._prog.set_ivec3("u_selBlock", int(inp.sel_x), int(inp.sel_y), int(inp.sel_z))
            self._prog.set_float("u_selTint", float(inp.sel_tint))

            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, int(self._atlas.tex_id))

            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, int(inp.shadow_info.tex_id) if shadow_sampling_ok else 0)

            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)

            for ck, ch in self._chunks.items():
                if not self._within_render_distance(ck, cam, rd):
                    continue
                if not self._chunk_intersects_view_volume(ck, view_proj):
                    continue

                for fi, (mesh, cnt) in enumerate(zip(ch.meshes, ch.counts)):
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