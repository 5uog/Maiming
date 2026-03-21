# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict
import math
import queue
import numpy as np

from ...math.vec3 import Vec3
from ...world.config.render_distance import clamp_render_distance_chunks
from ...math.chunking.chunk_grid import ChunkKey, chunk_key, normalize_chunk_key
from ...world.world_state import WorldState
from .gl_renderer import GLRenderer
from ...rendering.chunk_face_payload_cpu import build_chunk_face_payload_sources

@dataclass(frozen=True)
class _BuildResult:
    chunk: ChunkKey
    chunk_rev: int
    gpu_face_sources: np.ndarray
    gpu_bucket_counts: tuple[int, int, int, int, int, int]

class WorldUploadTracker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="WorldMeshBuild")
        self._pending: Dict[ChunkKey, Future] = {}
        self._pending_rev: Dict[ChunkKey, int] = {}
        self._want_rev: Dict[ChunkKey, int] = {}
        self._resident_rev: Dict[ChunkKey, int] = {}
        self._results: "queue.Queue[_BuildResult]" = queue.Queue()

    def reset(self, renderer: GLRenderer) -> None:
        self._evict_far_chunks(renderer=renderer, keep=set())
        while True:
            try:
                self._results.get_nowait()
            except queue.Empty:
                break

    def _retire_finished(self) -> None:
        for ck, fut in list(self._pending.items()):
            if not fut.done():
                continue
            self._pending.pop(ck, None)
            self._pending_rev.pop(ck, None)

    def _drain_results(self, renderer: GLRenderer) -> None:
        self._retire_finished()

        while True:
            try:
                r = self._results.get_nowait()
            except queue.Empty:
                break

            ck = normalize_chunk_key(r.chunk)
            want = self._want_rev.get(ck)
            if want is None or int(want) != int(r.chunk_rev):
                continue

            if int(self._resident_rev.get(ck, -1)) == int(r.chunk_rev):
                continue

            renderer.submit_chunk(chunk_key=ck, world_revision=int(r.chunk_rev), gpu_face_sources=r.gpu_face_sources, gpu_bucket_counts=r.gpu_bucket_counts)
            self._resident_rev[ck] = int(r.chunk_rev)

        self._retire_finished()

    @staticmethod
    def _center_chunk(eye: Vec3) -> ChunkKey:
        bx = int(math.floor(float(eye.x)))
        by = int(math.floor(float(eye.y)))
        bz = int(math.floor(float(eye.z)))
        return normalize_chunk_key(chunk_key(bx, by, bz))

    @staticmethod
    def _needed_chunks(existing: set[ChunkKey], center: ChunkKey, rd: int, y_pad: int = 1) -> list[ChunkKey]:
        cx, cy, cz = normalize_chunk_key(center)
        r = int(max(0, rd))

        out: list[ChunkKey] = []
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                for dy in range(-int(y_pad), int(y_pad) + 1):
                    ck = normalize_chunk_key((cx + dx, cy + dy, cz + dz))
                    if ck in existing:
                        out.append(ck)

        out.sort(key=lambda k: (abs(int(k[0]) - cx) + abs(int(k[2]) - cz), abs(int(k[1]) - cy)))
        return out

    @staticmethod
    def _retained_chunks(existing: set[ChunkKey], center: ChunkKey, rd: int, y_pad: int = 2, margin: int = 4) -> set[ChunkKey]:
        keep = WorldUploadTracker._needed_chunks(existing, center, int(max(0, int(rd))) + int(max(0, int(margin))), y_pad=int(max(0, int(y_pad))))
        return set(keep)

    def _evict_far_chunks(self, *, renderer: GLRenderer, keep: set[ChunkKey]) -> None:
        keep_n = {normalize_chunk_key(k) for k in keep}

        renderer.evict_chunks(keep_chunks=keep_n)

        for ck in list(self._resident_rev.keys()):
            if ck not in keep_n:
                del self._resident_rev[ck]

        for ck in list(self._want_rev.keys()):
            if ck not in keep_n:
                del self._want_rev[ck]

        for ck in list(self._pending.keys()):
            if ck not in keep_n:
                fut = self._pending.pop(ck)
                self._pending_rev.pop(ck, None)
                try:
                    fut.cancel()
                except Exception:
                    pass

    @staticmethod
    def _make_state_getter(state_at: dict[tuple[int, int, int], str]):
        def get_state(x: int, y: int, z: int) -> str | None:
            return state_at.get((int(x), int(y), int(z)))

        return get_state

    @staticmethod
    def _build_result_for_snapshot(chunk_key: ChunkKey, chunk_rev: int, blocks_local: list[tuple[int, int, int, str]], get_state, uv_lookup, def_lookup) -> _BuildResult:
        ck = normalize_chunk_key(chunk_key)
        gpu_face_sources, gpu_bucket_counts = build_chunk_face_payload_sources(blocks=blocks_local, get_state=get_state, uv_lookup=uv_lookup, def_lookup=def_lookup)
        return _BuildResult(chunk=ck, chunk_rev=int(chunk_rev), gpu_face_sources=gpu_face_sources, gpu_bucket_counts=gpu_bucket_counts)

    def _schedule_build(self, *, world: WorldState, renderer: GLRenderer, ck: ChunkKey, chunk_rev: int) -> None:
        ck = normalize_chunk_key(ck)
        tools = renderer.world_build_tools()
        if tools is None:
            return
        uv_lookup, def_lookup = tools

        if int(chunk_rev) <= 0:
            return

        if int(self._resident_rev.get(ck, -1)) == int(chunk_rev):
            self._want_rev[ck] = int(chunk_rev)
            return

        f = self._pending.get(ck)
        if f is not None and not f.done():
            self._want_rev[ck] = int(chunk_rev)
            if int(self._pending_rev.get(ck, -1)) == int(chunk_rev):
                return
            return

        self._want_rev[ck] = int(chunk_rev)

        blocks_local, state_at = world.snapshot_for_chunk_build(ck)
        get_state = self._make_state_getter(state_at)

        fut = self._executor.submit(self._build_result_for_snapshot, ck, int(chunk_rev), blocks_local, get_state, uv_lookup, def_lookup)

        def _on_done(done_fut: Future) -> None:
            try:
                res = done_fut.result()
            except Exception:
                return
            self._results.put(res)

        fut.add_done_callback(_on_done)
        self._pending[ck] = fut
        self._pending_rev[ck] = int(chunk_rev)

    def _schedule_chunks_if_stale(self, *, world: WorldState, renderer: GLRenderer, chunks: list[ChunkKey]) -> None:
        for ck0 in chunks:
            ck = normalize_chunk_key(ck0)
            cr = int(world.chunk_mesh_revision(ck))
            if cr <= 0:
                continue
            if int(self._resident_rev.get(ck, -1)) == int(cr):
                continue
            self._schedule_build(world=world, renderer=renderer, ck=ck, chunk_rev=int(cr))

    def upload_if_needed(self, *, world: WorldState, renderer: GLRenderer, eye: Vec3, render_distance_chunks: int) -> None:
        self._drain_results(renderer)

        existing = {normalize_chunk_key(ck) for ck in world.existing_chunk_keys()}
        if not existing:
            return

        center = self._center_chunk(eye)
        rd = clamp_render_distance_chunks(int(render_distance_chunks))

        visible = self._needed_chunks(existing, center, rd, y_pad=1)
        prefetch = self._needed_chunks(existing, center, rd + 2, y_pad=1)

        keep = self._retained_chunks(existing, center, rd, y_pad=2, margin=4)
        self._evict_far_chunks(renderer=renderer, keep=keep)

        dirty_map = world.consume_dirty_chunks_with_rev()
        for ck0, cr in dirty_map.items():
            ck = normalize_chunk_key(ck0)
            if ck in existing:
                self._schedule_build(world=world, renderer=renderer, ck=ck, chunk_rev=int(cr))

        self._schedule_chunks_if_stale(world=world, renderer=renderer, chunks=visible)
        self._schedule_chunks_if_stale(world=world, renderer=renderer, chunks=prefetch)

        self._drain_results(renderer)