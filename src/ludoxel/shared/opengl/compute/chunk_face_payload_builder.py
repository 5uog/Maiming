# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from OpenGL.GL import glDispatchCompute, glMemoryBarrier, GL_SHADER_STORAGE_BARRIER_BIT, GL_BUFFER_UPDATE_BARRIER_BIT

from ...math.chunking.chunk_grid import ChunkKey
from ...rendering.faces.face_bucket_layout import FACE_COUNT, BucketCounts, bucket_offsets, empty_face_bucket_arrays, normalize_bucket_counts
from ..gl.array_view import as_float32_rows
from ..gl.shader_program import ShaderProgram
from ..gl.storage_buffer import StorageBuffer


@dataclass(frozen=True)
class ChunkFacePayloadSnapshot:
    face_buckets: list[np.ndarray]
    last_rev: int


class ChunkFacePayloadBuilder:

    def __init__(self, *, local_size_x: int=64) -> None:
        self._prog: ShaderProgram | None = None
        self._src: StorageBuffer | None = None
        self._dst: StorageBuffer | None = None
        self._local_size_x = int(max(1, int(local_size_x)))
        self._chunks: dict[ChunkKey, ChunkFacePayloadSnapshot] = {}

    def initialize(self, prog: ShaderProgram) -> None:
        self._prog = prog
        self._src = StorageBuffer()
        self._dst = StorageBuffer()

    def destroy(self) -> None:
        if self._src is not None:
            self._src.destroy()
            self._src = None

        if self._dst is not None:
            self._dst.destroy()
            self._dst = None

        self._prog = None
        self._chunks.clear()

    def remove_chunk(self, chunk_key: ChunkKey) -> None:
        ck = (int(chunk_key[0]), int(chunk_key[1]), int(chunk_key[2]))
        self._chunks.pop(ck, None)

    def evict_except(self, keep: set[ChunkKey]) -> None:
        keep_n = {(int(k[0]), int(k[1]), int(k[2])) for k in keep}
        doomed = [ck for ck in self._chunks.keys() if ck not in keep_n]
        for ck in doomed:
            self.remove_chunk(ck)

    def _build_faces(self, *, face_sources: np.ndarray, bucket_counts: BucketCounts) -> list[np.ndarray]:
        if self._prog is None or self._src is None or self._dst is None:
            return empty_face_bucket_arrays(12)

        counts = normalize_bucket_counts(bucket_counts)
        total_rows = int(sum(int(c) for c in counts))
        if total_rows <= 0 or face_sources.size <= 0:
            return empty_face_bucket_arrays(12)

        src = as_float32_rows(face_sources, cols=14, label="GPU face payload sources")

        face_count = int(src.shape[0])
        if face_count <= 0:
            return empty_face_bucket_arrays(12)

        offsets = bucket_offsets(counts)
        out_bytes = int(total_rows) * 12 * 4

        self._src.upload_array(src.reshape(-1))
        self._dst.set_size(out_bytes)

        self._prog.use()
        self._prog.set_int("u_faceCount", int(face_count))
        self._prog.set_int("u_offset0", int(offsets[0]))
        self._prog.set_int("u_offset1", int(offsets[1]))
        self._prog.set_int("u_offset2", int(offsets[2]))
        self._prog.set_int("u_offset3", int(offsets[3]))
        self._prog.set_int("u_offset4", int(offsets[4]))
        self._prog.set_int("u_offset5", int(offsets[5]))

        self._src.bind_base(0)
        self._dst.bind_base(1)

        try:
            groups_x = int((face_count + self._local_size_x - 1) // self._local_size_x)
            glDispatchCompute(int(groups_x), 1, 1)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT | GL_BUFFER_UPDATE_BARRIER_BIT)
        finally:
            self._src.unbind_base(0)
            self._dst.unbind_base(1)

        raw = np.frombuffer(self._dst.read_bytes(out_bytes), dtype=np.float32).copy()
        raw = raw.reshape((int(total_rows), 12))

        out: list[np.ndarray] = []
        for fi in range(FACE_COUNT):
            n = int(counts[fi])
            if n <= 0:
                out.append(np.zeros((0, 12), dtype=np.float32))
                continue

            start = int(offsets[fi])
            end = int(start + n)
            out.append(np.ascontiguousarray(raw[start:end], dtype=np.float32))

        return out

    def build_and_store(self, *, chunk_key: ChunkKey, world_revision: int, face_sources: np.ndarray, bucket_counts: BucketCounts) -> ChunkFacePayloadSnapshot:
        ck = (int(chunk_key[0]), int(chunk_key[1]), int(chunk_key[2]))
        prev = self._chunks.get(ck)
        if prev is not None and int(prev.last_rev) == int(world_revision):
            return prev

        face_buckets = self._build_faces(face_sources=face_sources, bucket_counts=bucket_counts)

        snap = ChunkFacePayloadSnapshot(face_buckets=face_buckets, last_rev=int(world_revision))
        self._chunks[ck] = snap
        return snap
