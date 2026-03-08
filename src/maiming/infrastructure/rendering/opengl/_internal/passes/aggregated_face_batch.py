# FILE: src/maiming/infrastructure/rendering/opengl/_internal/passes/aggregated_face_batch.py
from __future__ import annotations

from ctypes import c_void_p
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from OpenGL.GL import (
    glGenBuffers,
    glDeleteBuffers,
    glBindBuffer,
    glBufferData,
    glBufferSubData,
    glBindVertexArray,
    glMultiDrawArraysIndirect,
    GL_DRAW_INDIRECT_BUFFER,
    GL_STREAM_DRAW,
    GL_TRIANGLES,
)

from maiming.domain.world.chunking import ChunkKey
from maiming.infrastructure.rendering.opengl._internal.gl.mesh_buffer import MeshBuffer

@dataclass(frozen=True)
class _ChunkSlice:
    offsets: tuple[int, int, int, int, int, int]
    counts: tuple[int, int, int, int, int, int]
    last_rev: int

class AggregatedFaceBatch:
    def __init__(self) -> None:
        self._initialized = False

        self._meshes: list[MeshBuffer] = []
        self._indirect_buffers: list[int] = []
        self._indirect_caps: list[int] = [0, 0, 0, 0, 0, 0]

        self._source_faces: dict[ChunkKey, list[np.ndarray]] = {}
        self._source_revs: dict[ChunkKey, int] = {}
        self._source_instance_total: int = 0

        self._ordered_chunks: tuple[ChunkKey, ...] = ()
        self._chunk_slices: dict[ChunkKey, _ChunkSlice] = {}

        self._dirty = True

    @staticmethod
    def _empty_face_array() -> np.ndarray:
        return np.zeros((0, 12), dtype=np.float32)

    @staticmethod
    def _norm_face_array(arr: np.ndarray) -> np.ndarray:
        src = arr
        if src.dtype != np.float32:
            src = src.astype(np.float32, copy=False)
        if not src.flags["C_CONTIGUOUS"]:
            src = np.ascontiguousarray(src, dtype=np.float32)
        else:
            src = src.copy()

        if src.ndim != 2 or src.shape[1] != 12:
            raise ValueError("Aggregated face payload rows must be float32 Nx12 arrays")

        return src

    @staticmethod
    def _chunk_total(faces: list[np.ndarray]) -> int:
        total = 0
        for arr in faces[:6]:
            total += int(arr.shape[0])
        return int(total)

    def initialize(self) -> None:
        if bool(self._initialized):
            return

        self._meshes = [MeshBuffer.create_quad_instanced(i) for i in range(6)]
        self._indirect_buffers = [int(glGenBuffers(1)) for _ in range(6)]
        self._indirect_caps = [0, 0, 0, 0, 0, 0]

        self._initialized = True
        self._dirty = True

    def destroy(self) -> None:
        for mesh in self._meshes:
            mesh.destroy()
        self._meshes = []

        for buf in self._indirect_buffers:
            if int(buf) != 0:
                glDeleteBuffers(1, [int(buf)])
        self._indirect_buffers = []
        self._indirect_caps = [0, 0, 0, 0, 0, 0]

        self._initialized = False
        self._dirty = True

    def total_instances(self) -> int:
        return int(self._source_instance_total)

    def set_chunk_faces(
        self,
        *,
        chunk_key: ChunkKey,
        world_revision: int,
        faces: list[np.ndarray],
    ) -> None:
        if len(faces) != 6:
            return

        ck = (int(chunk_key[0]), int(chunk_key[1]), int(chunk_key[2]))
        prev_rev = self._source_revs.get(ck)
        if prev_rev is not None and int(prev_rev) == int(world_revision):
            return

        prev_faces = self._source_faces.get(ck)
        if prev_faces is not None:
            self._source_instance_total -= self._chunk_total(prev_faces)

        norm_faces = [self._norm_face_array(arr) for arr in faces]
        self._source_faces[ck] = norm_faces
        self._source_revs[ck] = int(world_revision)
        self._source_instance_total += self._chunk_total(norm_faces)
        self._dirty = True

    def remove_chunk(self, chunk_key: ChunkKey) -> None:
        ck = (int(chunk_key[0]), int(chunk_key[1]), int(chunk_key[2]))
        prev_faces = self._source_faces.pop(ck, None)
        self._source_revs.pop(ck, None)
        self._chunk_slices.pop(ck, None)

        if prev_faces is not None:
            self._source_instance_total -= self._chunk_total(prev_faces)
            self._dirty = True

    def evict_except(self, keep: set[ChunkKey]) -> None:
        keep_n = {(int(k[0]), int(k[1]), int(k[2])) for k in keep}
        doomed = [ck for ck in self._source_faces.keys() if ck not in keep_n]
        if not doomed:
            return

        for ck in doomed:
            prev_faces = self._source_faces.pop(ck, None)
            self._source_revs.pop(ck, None)
            self._chunk_slices.pop(ck, None)
            if prev_faces is not None:
                self._source_instance_total -= self._chunk_total(prev_faces)

        self._dirty = True

    def prepare(self) -> None:
        if not bool(self._dirty):
            return

        ordered = tuple(sorted(self._source_faces.keys()))
        merged: list[list[np.ndarray]] = [[] for _ in range(6)]
        offsets = [0, 0, 0, 0, 0, 0]
        slices: dict[ChunkKey, _ChunkSlice] = {}

        for ck in ordered:
            faces = self._source_faces[ck]
            counts = tuple(int(arr.shape[0]) for arr in faces[:6])
            slice_offsets = tuple(int(v) for v in offsets[:6])

            slices[ck] = _ChunkSlice(
                offsets=slice_offsets,
                counts=(
                    int(counts[0]),
                    int(counts[1]),
                    int(counts[2]),
                    int(counts[3]),
                    int(counts[4]),
                    int(counts[5]),
                ),
                last_rev=int(self._source_revs.get(ck, -1)),
            )

            for fi in range(6):
                arr = faces[fi]
                if int(arr.shape[0]) > 0:
                    merged[fi].append(arr)
                    offsets[fi] += int(arr.shape[0])

        self._ordered_chunks = ordered
        self._chunk_slices = slices

        if bool(self._initialized):
            for fi in range(6):
                if merged[fi]:
                    data = np.concatenate(merged[fi], axis=0)
                else:
                    data = self._empty_face_array()
                self._meshes[fi].upload_instances(data)

        self._dirty = False

    def chunk_keys(self) -> tuple[ChunkKey, ...]:
        self.prepare()
        return self._ordered_chunks

    def build_commands(self, chunks: Iterable[ChunkKey]) -> list[np.ndarray]:
        self.prepare()

        rows: list[list[tuple[int, int, int, int]]] = [[] for _ in range(6)]

        for ck0 in chunks:
            ck = (int(ck0[0]), int(ck0[1]), int(ck0[2]))
            sl = self._chunk_slices.get(ck)
            if sl is None:
                continue

            for fi in range(6):
                cnt = int(sl.counts[fi])
                if cnt <= 0:
                    continue

                rows[fi].append(
                    (
                        int(self._meshes[fi].vertex_count) if self._meshes else 6,
                        int(cnt),
                        0,
                        int(sl.offsets[fi]),
                    )
                )

        out: list[np.ndarray] = []
        for fi in range(6):
            if not rows[fi]:
                out.append(np.zeros((0, 4), dtype=np.uint32))
                continue

            arr = np.asarray(rows[fi], dtype=np.uint32)
            if not arr.flags["C_CONTIGUOUS"]:
                arr = np.ascontiguousarray(arr, dtype=np.uint32)
            out.append(arr)

        return out

    def _upload_indirect(self, face_idx: int, commands: np.ndarray) -> None:
        fi = int(face_idx)
        if fi < 0 or fi >= len(self._indirect_buffers):
            return

        arr = commands
        if arr.dtype != np.uint32:
            arr = arr.astype(np.uint32, copy=False)
        if not arr.flags["C_CONTIGUOUS"]:
            arr = np.ascontiguousarray(arr, dtype=np.uint32)

        nbytes = int(arr.nbytes)
        buf = int(self._indirect_buffers[fi])

        glBindBuffer(GL_DRAW_INDIRECT_BUFFER, buf)
        if nbytes <= 0:
            glBufferData(GL_DRAW_INDIRECT_BUFFER, 0, None, GL_STREAM_DRAW)
            self._indirect_caps[fi] = 0
            glBindBuffer(GL_DRAW_INDIRECT_BUFFER, 0)
            return

        cap = int(self._indirect_caps[fi])
        if cap > 0 and nbytes <= cap:
            glBufferSubData(GL_DRAW_INDIRECT_BUFFER, 0, nbytes, arr)
        else:
            glBufferData(GL_DRAW_INDIRECT_BUFFER, nbytes, arr, GL_STREAM_DRAW)
            self._indirect_caps[fi] = int(nbytes)

        glBindBuffer(GL_DRAW_INDIRECT_BUFFER, 0)

    def draw(
        self,
        commands: list[np.ndarray],
        *,
        before_face_draw: Callable[[int], None] | None = None,
    ) -> tuple[int, int]:
        if not bool(self._initialized):
            return (0, 0)

        draw_calls = 0
        instances = 0

        for fi in range(min(6, len(commands))):
            cmd = commands[fi]
            if cmd.size <= 0 or int(cmd.shape[0]) <= 0:
                continue

            self._upload_indirect(int(fi), cmd)

            if before_face_draw is not None:
                before_face_draw(int(fi))

            mesh = self._meshes[fi]
            glBindVertexArray(int(mesh.vao))
            glBindBuffer(GL_DRAW_INDIRECT_BUFFER, int(self._indirect_buffers[fi]))
            glMultiDrawArraysIndirect(GL_TRIANGLES, c_void_p(0), int(cmd.shape[0]), 0)
            glBindBuffer(GL_DRAW_INDIRECT_BUFFER, 0)
            glBindVertexArray(0)

            draw_calls += 1
            instances += int(np.sum(cmd[:, 1], dtype=np.uint64))

        return (int(draw_calls), int(instances))