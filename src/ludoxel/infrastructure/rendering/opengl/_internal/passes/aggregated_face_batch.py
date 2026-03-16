# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/passes/aggregated_face_batch.py
from __future__ import annotations

from ctypes import c_void_p
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from OpenGL.GL import glGenBuffers, glDeleteBuffers, glMultiDrawArraysIndirect, glBindBuffer, glBindVertexArray, GL_DRAW_INDIRECT_BUFFER, GL_STREAM_DRAW, GL_TRIANGLES

from ......domain.world.chunking import ChunkKey, normalize_chunk_key
from ..face_bucket_layout import FACE_COUNT
from ..gl.array_view import as_uint32_rows, copy_float32_rows
from ..gl.buffer_upload import upload_array_buffer
from ..gl.mesh_buffer import MeshBuffer


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
        self._indirect_caps: list[int] = [0 for _ in range(FACE_COUNT)]

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
        return copy_float32_rows(arr, cols=12, label="Aggregated face payload rows")

    @staticmethod
    def _chunk_total(faces: list[np.ndarray]) -> int:
        total = 0
        for arr in faces[:FACE_COUNT]:
            total += int(arr.shape[0])
        return int(total)

    def initialize(self) -> None:
        if bool(self._initialized):
            return

        self._meshes = [MeshBuffer.create_quad_instanced(i) for i in range(FACE_COUNT)]
        self._indirect_buffers = [int(glGenBuffers(1)) for _ in range(FACE_COUNT)]
        self._indirect_caps = [0 for _ in range(FACE_COUNT)]

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
        self._indirect_caps = [0 for _ in range(FACE_COUNT)]

        self._initialized = False
        self._dirty = True

    def total_instances(self) -> int:
        return int(self._source_instance_total)

    def set_chunk_faces(self, *, chunk_key: ChunkKey, world_revision: int, faces: list[np.ndarray]) -> None:
        if len(faces) != FACE_COUNT:
            return

        ck = normalize_chunk_key(chunk_key)
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
        ck = normalize_chunk_key(chunk_key)
        prev_faces = self._source_faces.pop(ck, None)
        self._source_revs.pop(ck, None)
        self._chunk_slices.pop(ck, None)

        if prev_faces is not None:
            self._source_instance_total -= self._chunk_total(prev_faces)
            self._dirty = True

    def evict_except(self, keep: set[ChunkKey]) -> None:
        keep_n = {normalize_chunk_key(k) for k in keep}
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
        merged: list[list[np.ndarray]] = [[] for _ in range(FACE_COUNT)]
        offsets = [0 for _ in range(FACE_COUNT)]
        slices: dict[ChunkKey, _ChunkSlice] = {}

        for ck in ordered:
            faces = self._source_faces[ck]
            counts = tuple(int(arr.shape[0]) for arr in faces[:FACE_COUNT])
            slice_offsets = tuple(int(v) for v in offsets[:FACE_COUNT])

            slices[ck] = _ChunkSlice(offsets=slice_offsets, counts=(int(counts[0]), int(counts[1]), int(counts[2]), int(counts[3]), int(counts[4]), int(counts[5])), last_rev=int(self._source_revs.get(ck, -1)))

            for fi in range(FACE_COUNT):
                arr = faces[fi]
                if int(arr.shape[0]) > 0:
                    merged[fi].append(arr)
                    offsets[fi] += int(arr.shape[0])

        self._ordered_chunks = ordered
        self._chunk_slices = slices

        if bool(self._initialized):
            for fi in range(FACE_COUNT):
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

        rows: list[list[tuple[int, int, int, int]]] = [[] for _ in range(FACE_COUNT)]

        for ck0 in chunks:
            ck = normalize_chunk_key(ck0)
            sl = self._chunk_slices.get(ck)
            if sl is None:
                continue

            for fi in range(FACE_COUNT):
                cnt = int(sl.counts[fi])
                if cnt <= 0:
                    continue

                rows[fi].append((int(self._meshes[fi].vertex_count) if self._meshes else 6, int(cnt), 0, int(sl.offsets[fi])))

        out: list[np.ndarray] = []
        for fi in range(FACE_COUNT):
            if not rows[fi]:
                out.append(np.zeros((0, 4), dtype=np.uint32))
                continue

            arr = np.asarray(rows[fi], dtype=np.uint32)
            out.append(as_uint32_rows(arr, cols=4, label="Indirect draw commands"))

        return out

    def _upload_indirect(self, face_idx: int, commands: np.ndarray) -> None:
        fi = int(face_idx)
        if fi < 0 or fi >= len(self._indirect_buffers):
            return

        arr = as_uint32_rows(commands, cols=4, label="Indirect draw commands")
        self._indirect_caps[fi] = upload_array_buffer(target=GL_DRAW_INDIRECT_BUFFER, buffer=int(self._indirect_buffers[fi]), usage=GL_STREAM_DRAW, data=arr, capacity_bytes=int(self._indirect_caps[fi]))

    def draw(self, commands: list[np.ndarray], *, before_face_draw: Callable[[int], None] | None=None) -> tuple[int, int]:
        if not bool(self._initialized):
            return (0, 0)

        draw_calls = 0
        instances = 0

        for fi in range(min(FACE_COUNT, len(commands))):
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
