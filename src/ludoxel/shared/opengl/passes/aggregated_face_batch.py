# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ctypes import c_void_p
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from OpenGL.GL import GL_DRAW_INDIRECT_BUFFER, GL_STREAM_DRAW, GL_TRIANGLES, glBindBuffer, glBindVertexArray, glDeleteBuffers, glGenBuffers, glMultiDrawArraysIndirect

from ...math.chunking.chunk_grid import ChunkKey, normalize_chunk_key
from ...rendering.face_bucket_layout import FACE_COUNT
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

        self._source_revs: dict[ChunkKey, int] = {}
        self._source_instance_total: int = 0
        self._revision: int = 0

        self._chunk_slices: dict[ChunkKey, _ChunkSlice] = {}
        self._ordered_chunks: tuple[ChunkKey, ...] = ()
        self._dirty = True

        self._face_storage: list[np.ndarray] = [np.zeros((0, 12), dtype=np.float32) for _ in range(FACE_COUNT)]
        self._face_committed_rows: list[int] = [0 for _ in range(FACE_COUNT)]
        self._face_live_rows: list[int] = [0 for _ in range(FACE_COUNT)]
        self._free_ranges: list[list[tuple[int, int]]] = [[] for _ in range(FACE_COUNT)]

    @staticmethod
    def _empty_face_array() -> np.ndarray:
        return np.zeros((0, 12), dtype=np.float32)

    @staticmethod
    def _norm_face_array(arr: np.ndarray) -> np.ndarray:
        return copy_float32_rows(arr, cols=12, label="Aggregated face payload rows")

    @staticmethod
    def _chunk_total_from_slice(chunk_slice: _ChunkSlice | None) -> int:
        if chunk_slice is None:
            return 0
        total = 0
        for count in chunk_slice.counts:
            total += int(count)
        return int(total)

    def initialize(self) -> None:
        if bool(self._initialized):
            return

        self._meshes = [MeshBuffer.create_quad_instanced(i) for i in range(FACE_COUNT)]
        self._indirect_buffers = [int(glGenBuffers(1)) for _ in range(FACE_COUNT)]
        self._indirect_caps = [0 for _ in range(FACE_COUNT)]

        self._initialized = True
        for fi in range(FACE_COUNT):
            self._meshes[fi].upload_instances(self._committed_face_rows(fi))
        self._dirty = True

    def destroy(self) -> None:
        for mesh in self._meshes:
            mesh.destroy()
        self._meshes = []

        for buf in self._indirect_buffers:
            if int(buf) != 0:
                glDeleteBuffers(1,[int(buf)])
        self._indirect_buffers = []
        self._indirect_caps = [0 for _ in range(FACE_COUNT)]

        self._initialized = False
        self._dirty = True

    def total_instances(self) -> int:
        return int(self._source_instance_total)

    def revision(self) -> int:
        return int(self._revision)

    def _merge_free_ranges(self, face_idx: int) -> None:
        merged: list[tuple[int, int]] = []
        for offset, length in sorted(self._free_ranges[int(face_idx)], key=lambda item: (int(item[0]), int(item[1]))):
            if int(length) <= 0:
                continue
            if not merged:
                merged.append((int(offset), int(length)))
                continue
            last_offset, last_length = merged[-1]
            if int(last_offset) + int(last_length) == int(offset):
                merged[-1] = (int(last_offset), int(last_length) + int(length))
            else:
                merged.append((int(offset), int(length)))
        self._free_ranges[int(face_idx)] = merged

    def _free_range(self, face_idx: int, offset: int, length: int) -> None:
        if int(length) <= 0:
            return
        self._free_ranges[int(face_idx)].append((int(offset), int(length)))
        self._merge_free_ranges(int(face_idx))

    def _ensure_face_capacity(self, face_idx: int, required_rows: int) -> bool:
        fi = int(face_idx)
        if int(required_rows) <= int(self._face_storage[fi].shape[0]):
            return False

        current_rows = int(self._face_storage[fi].shape[0])
        next_rows = max(int(required_rows), max(64, current_rows * 2))
        expanded = np.zeros((int(next_rows), 12), dtype=np.float32)
        if current_rows > 0:
            expanded[:current_rows] = self._face_storage[fi][:current_rows]
        self._face_storage[fi] = expanded
        return True

    def _allocate_range(self, face_idx: int, count: int) -> int:
        fi = int(face_idx)
        need = int(count)
        if need <= 0:
            return 0

        best_idx: int | None = None
        best_length = 0
        for index, (offset, length) in enumerate(self._free_ranges[fi]):
            if int(length) < need:
                continue
            if best_idx is None or int(length) < best_length:
                best_idx = int(index)
                best_length = int(length)

        if best_idx is not None:
            offset, length = self._free_ranges[fi].pop(int(best_idx))
            if int(length) > need:
                self._free_ranges[fi].append((int(offset) + need, int(length) - need))
                self._merge_free_ranges(fi)
            return int(offset)

        offset = int(self._face_committed_rows[fi])
        self._face_committed_rows[fi] = int(offset + need)
        self._ensure_face_capacity(fi, int(self._face_committed_rows[fi]))
        return int(offset)

    def _committed_face_rows(self, face_idx: int) -> np.ndarray:
        fi = int(face_idx)
        committed_rows = int(self._face_committed_rows[fi])
        if committed_rows <= 0:
            return self._empty_face_array()
        return self._face_storage[fi][:committed_rows]

    def _should_compact_face(self, face_idx: int) -> bool:
        fi = int(face_idx)
        live_rows = int(self._face_live_rows[fi])
        committed_rows = int(self._face_committed_rows[fi])
        slack_rows = int(committed_rows - live_rows)

        if committed_rows <= 0:
            return bool(self._free_ranges[fi])
        if live_rows <= 0:
            return True
        if slack_rows <= 0:
            return False
        if slack_rows >= max(256, int(live_rows // 3)):
            return True
        return len(self._free_ranges[fi]) >= 16 and slack_rows >= max(64, int(live_rows // 8))

    def _compact_face(self, face_idx: int) -> None:
        fi = int(face_idx)
        live_rows = int(self._face_live_rows[fi])

        if live_rows <= 0:
            self._face_storage[fi] = self._empty_face_array()
            self._face_committed_rows[fi] = 0
            self._free_ranges[fi] = []
            if bool(self._initialized):
                self._meshes[fi].upload_instances(self._empty_face_array())
            return

        compact = np.zeros((live_rows, 12), dtype=np.float32)
        cursor = 0

        for ck in tuple(sorted(self._chunk_slices.keys())):
            chunk_slice = self._chunk_slices.get(ck)
            if chunk_slice is None:
                continue

            count = int(chunk_slice.counts[fi])
            offsets = list(chunk_slice.offsets)
            if count > 0:
                offset = int(chunk_slice.offsets[fi])
                compact[cursor:cursor + count] = self._face_storage[fi][offset:offset + count]
                offsets[fi] = int(cursor)
                cursor += int(count)
            else:
                offsets[fi] = 0

            self._chunk_slices[ck] = _ChunkSlice(offsets=(int(offsets[0]), int(offsets[1]), int(offsets[2]), int(offsets[3]), int(offsets[4]), int(offsets[5])), counts=chunk_slice.counts, last_rev=int(chunk_slice.last_rev))

        self._face_storage[fi] = compact
        self._face_committed_rows[fi] = int(live_rows)
        self._free_ranges[fi] = []

        if bool(self._initialized):
            self._meshes[fi].upload_instances(compact)

    def _maybe_compact_face(self, face_idx: int) -> None:
        fi = int(face_idx)
        if not self._should_compact_face(fi):
            return
        self._compact_face(fi)

    def _store_face_rows(self, face_idx: int, offset: int, rows: np.ndarray) -> None:
        fi = int(face_idx)
        arr = self._norm_face_array(rows)
        if int(arr.shape[0]) <= 0:
            return

        grew = self._ensure_face_capacity(fi, int(offset) + int(arr.shape[0]))
        self._face_storage[fi][int(offset):int(offset) + int(arr.shape[0])] = arr

        if not bool(self._initialized):
            return
        required_bytes = (int(offset) + int(arr.shape[0])) * 12 * 4
        if bool(grew) or int(self._meshes[fi].instance_capacity) < int(required_bytes):
            self._meshes[fi].upload_instances(self._committed_face_rows(fi))
            return
        self._meshes[fi].upload_instances_subrange(arr, row_offset=int(offset))

    def set_chunk_faces(self, *, chunk_key: ChunkKey, world_revision: int, faces: list[np.ndarray]) -> None:
        if len(faces) != FACE_COUNT:
            return

        ck = normalize_chunk_key(chunk_key)
        prev_rev = self._source_revs.get(ck)
        if prev_rev is not None and int(prev_rev) == int(world_revision):
            return

        old_slice = self._chunk_slices.get(ck)
        old_total = self._chunk_total_from_slice(old_slice)
        new_offsets = [0 for _ in range(FACE_COUNT)]
        new_counts = [0 for _ in range(FACE_COUNT)]
        compact_faces: set[int] = set()

        normalized_faces = [self._norm_face_array(arr) for arr in faces]

        for fi in range(FACE_COUNT):
            arr = normalized_faces[fi]
            new_count = int(arr.shape[0])
            old_offset = 0 if old_slice is None else int(old_slice.offsets[fi])
            old_count = 0 if old_slice is None else int(old_slice.counts[fi])

            if new_count > 0 and new_count == old_count and old_count > 0:
                new_offsets[fi] = int(old_offset)
                new_counts[fi] = int(new_count)
                self._store_face_rows(fi, int(old_offset), arr)
                continue

            if old_count > 0:
                self._free_range(fi, int(old_offset), int(old_count))
                compact_faces.add(int(fi))

            if new_count > 0:
                new_offset = self._allocate_range(fi, int(new_count))
                new_offsets[fi] = int(new_offset)
                new_counts[fi] = int(new_count)
                self._store_face_rows(fi, int(new_offset), arr)

        new_total = sum(int(count) for count in new_counts)
        self._source_instance_total += int(new_total) - int(old_total)
        self._source_revs[ck] = int(world_revision)

        if int(new_total) <= 0:
            self._chunk_slices.pop(ck, None)
        else:
            self._chunk_slices[ck] = _ChunkSlice(offsets=(int(new_offsets[0]), int(new_offsets[1]), int(new_offsets[2]), int(new_offsets[3]), int(new_offsets[4]), int(new_offsets[5])), counts=(int(new_counts[0]), int(new_counts[1]), int(new_counts[2]), int(new_counts[3]), int(new_counts[4]), int(new_counts[5])), last_rev=int(world_revision))

        for fi in range(FACE_COUNT):
            old_count = 0 if old_slice is None else int(old_slice.counts[fi])
            self._face_live_rows[fi] += int(new_counts[fi]) - int(old_count)
            if int(old_count) != int(new_counts[fi]):
                compact_faces.add(int(fi))

        for fi in sorted(compact_faces):
            self._maybe_compact_face(int(fi))

        self._revision += 1
        self._dirty = True

    def remove_chunk(self, chunk_key: ChunkKey) -> None:
        ck = normalize_chunk_key(chunk_key)
        old_slice = self._chunk_slices.pop(ck, None)
        self._source_revs.pop(ck, None)
        if old_slice is None:
            return

        for fi in range(FACE_COUNT):
            count = int(old_slice.counts[fi])
            if count <= 0:
                continue
            self._free_range(fi, int(old_slice.offsets[fi]), int(count))
            self._face_live_rows[fi] -= int(count)
            self._maybe_compact_face(int(fi))

        self._source_instance_total -= self._chunk_total_from_slice(old_slice)
        self._revision += 1
        self._dirty = True

    def evict_except(self, keep: set[ChunkKey]) -> None:
        keep_n = {normalize_chunk_key(k) for k in keep}
        doomed = [ck for ck in set(self._chunk_slices.keys()) | set(self._source_revs.keys()) if ck not in keep_n]
        if not doomed:
            return

        for ck in doomed:
            self.remove_chunk(ck)

    def prepare(self) -> None:
        if not bool(self._dirty):
            return
        self._ordered_chunks = tuple(sorted(self._chunk_slices.keys()))
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
