# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections import OrderedDict
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
from ...rendering.faces.chunk_face_payload_cpu import build_chunk_mesh_cpu


@dataclass(frozen=True)
class _BuildResult:
    world_token: int
    chunk: ChunkKey
    chunk_rev: int
    faces: tuple[np.ndarray, ...]


class WorldUploadTracker:

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="WorldMeshBuild")
        self._pending: Dict[tuple[int, ChunkKey], Future] = {}
        self._pending_rev: Dict[tuple[int, ChunkKey], int] = {}
        self._want_rev: Dict[ChunkKey, int] = {}
        self._resident_rev: Dict[ChunkKey, int] = {}
        self._results: "queue.Queue[_BuildResult]" = queue.Queue()
        self._max_results_per_drain: int = 4
        self._active_world_token: int | None = None
        self._visible_cache_key: tuple[int, int, int, ChunkKey, int] | None = None
        self._visible_cache_chunks: tuple[ChunkKey, ...] = ()
        self._build_cache: "OrderedDict[tuple[int, ChunkKey, int], _BuildResult]" = OrderedDict()
        self._max_cached_results: int = 192

    @staticmethod
    def _world_token(world: WorldState) -> int:
        return int(id(world))

    @staticmethod
    def _pending_key(world_token: int, chunk: ChunkKey) -> tuple[int, ChunkKey]:
        return (int(world_token), normalize_chunk_key(chunk))

    @staticmethod
    def _build_cache_key(world_token: int, chunk: ChunkKey, chunk_rev: int) -> tuple[int, ChunkKey, int]:
        return (int(world_token), normalize_chunk_key(chunk), int(chunk_rev))

    def _store_cached_result(self, result: _BuildResult) -> None:
        ck = normalize_chunk_key(result.chunk)
        prefix = (int(result.world_token), ck)
        for cache_key in list(self._build_cache.keys()):
            if cache_key[:2] != prefix:
                continue
            if int(cache_key[2]) == int(result.chunk_rev):
                self._build_cache.pop(cache_key, None)
                continue
            self._build_cache.pop(cache_key, None)

        cache_key = self._build_cache_key(int(result.world_token), ck, int(result.chunk_rev))
        self._build_cache[cache_key] = result
        self._build_cache.move_to_end(cache_key)

        while len(self._build_cache) > int(self._max_cached_results):
            self._build_cache.popitem(last=False)

    def reset(self, renderer: GLRenderer, *, world: WorldState | None=None) -> None:
        renderer.evict_chunks(keep_chunks=set())
        self._active_world_token = None if world is None else self._world_token(world)
        self._want_rev.clear()
        self._resident_rev.clear()
        self._visible_cache_key = None
        self._visible_cache_chunks = ()
        while True:
            try:
                self._results.get_nowait()
            except queue.Empty:
                break
        for pending_key, fut in list(self._pending.items()):
            self._pending.pop(pending_key, None)
            self._pending_rev.pop(pending_key, None)
            try:
                fut.cancel()
            except Exception:
                pass

    def _retire_finished(self) -> None:
        for pending_key, fut in list(self._pending.items()):
            if not fut.done():
                continue
            self._pending.pop(pending_key, None)
            self._pending_rev.pop(pending_key, None)

    def _drain_results(self, renderer: GLRenderer, *, world: WorldState) -> None:
        active_world_token = self._world_token(world)
        self._active_world_token = int(active_world_token)
        self._retire_finished()
        drained = 0

        while True:
            if drained >= int(self._max_results_per_drain):
                break
            try:
                r = self._results.get_nowait()
            except queue.Empty:
                break

            if int(r.world_token) != int(active_world_token):
                continue

            ck = normalize_chunk_key(r.chunk)
            want = self._want_rev.get(ck)
            if want is None or int(want) != int(r.chunk_rev):
                continue

            if int(self._resident_rev.get(ck, -1)) == int(r.chunk_rev):
                continue

            renderer.submit_chunk(chunk_key=ck, world_revision=int(r.chunk_rev), faces=list(r.faces))
            self._resident_rev[ck] = int(r.chunk_rev)
            drained += 1

        self._retire_finished()

    @staticmethod
    def _center_chunk(eye: Vec3) -> ChunkKey:
        bx = int(math.floor(float(eye.x)))
        by = int(math.floor(float(eye.y)))
        bz = int(math.floor(float(eye.z)))
        return normalize_chunk_key(chunk_key(bx, by, bz))

    @staticmethod
    def _needed_chunks(existing: set[ChunkKey], center: ChunkKey, rd: int, y_pad: int=1) -> list[ChunkKey]:
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
    def _retained_chunks(existing: set[ChunkKey], center: ChunkKey, rd: int, y_pad: int=2, margin: int=4) -> set[ChunkKey]:
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

        active_world_token = self._active_world_token
        for pending_key in list(self._pending.keys()):
            world_token, ck = pending_key
            if active_world_token is None or int(world_token) != int(active_world_token) or ck in keep_n:
                continue
            fut = self._pending.pop(pending_key)
            self._pending_rev.pop(pending_key, None)
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
    def _build_result_for_snapshot(world_token: int, chunk_key: ChunkKey, chunk_rev: int, blocks_local: list[tuple[int, int, int, str]], get_state, uv_lookup, def_lookup) -> _BuildResult:
        ck = normalize_chunk_key(chunk_key)
        faces_np, _shadow_faces_np = build_chunk_mesh_cpu(blocks=blocks_local, get_state=get_state, uv_lookup=uv_lookup, def_lookup=def_lookup)
        return _BuildResult(world_token=int(world_token), chunk=ck, chunk_rev=int(chunk_rev), faces=tuple(faces_np))

    def _schedule_build(self, *, world: WorldState, renderer: GLRenderer, ck: ChunkKey, chunk_rev: int) -> None:
        ck = normalize_chunk_key(ck)
        world_token = self._world_token(world)
        active_matches = int(world_token) == int(self._active_world_token if self._active_world_token is not None else world_token)
        tools = renderer.world_build_tools()
        if tools is None:
            return
        uv_lookup, def_lookup = tools

        if int(chunk_rev) <= 0:
            return

        if bool(active_matches):
            self._want_rev[ck] = int(chunk_rev)

        if bool(active_matches) and int(self._resident_rev.get(ck, -1)) == int(chunk_rev):
            self._want_rev[ck] = int(chunk_rev)
            return

        cache_key = self._build_cache_key(int(world_token), ck, int(chunk_rev))
        cached = self._build_cache.get(cache_key)
        if cached is not None:
            if bool(active_matches):
                self._results.put(cached)
            return

        pending_key = self._pending_key(int(world_token), ck)
        f = self._pending.get(pending_key)
        if f is not None and not f.done():
            if int(self._pending_rev.get(pending_key, -1)) == int(chunk_rev):
                return
            try:
                if not bool(f.cancel()):
                    return
            except Exception:
                return
            self._pending.pop(pending_key, None)
            self._pending_rev.pop(pending_key, None)

        blocks_local, state_at = world.snapshot_for_chunk_build(ck)
        get_state = self._make_state_getter(state_at)

        fut = self._executor.submit(self._build_result_for_snapshot, int(world_token), ck, int(chunk_rev), blocks_local, get_state, uv_lookup, def_lookup)

        def _on_done(done_fut: Future) -> None:
            try:
                res = done_fut.result()
            except Exception:
                return
            self._store_cached_result(res)
            if int(res.world_token) == int(self._active_world_token if self._active_world_token is not None else res.world_token):
                self._results.put(res)

        fut.add_done_callback(_on_done)
        self._pending[pending_key] = fut
        self._pending_rev[pending_key] = int(chunk_rev)

    def _schedule_chunks_if_stale(self, *, world: WorldState, renderer: GLRenderer, chunks: list[ChunkKey]) -> None:
        world_token = self._world_token(world)
        active_matches = int(world_token) == int(self._active_world_token if self._active_world_token is not None else world_token)
        for ck0 in chunks:
            ck = normalize_chunk_key(ck0)
            cr = int(world.chunk_mesh_revision(ck))
            if cr <= 0:
                continue
            if bool(active_matches) and int(self._resident_rev.get(ck, -1)) == int(cr):
                continue
            self._schedule_build(world=world, renderer=renderer, ck=ck, chunk_rev=int(cr))

    def has_ready_results(self) -> bool:
        return not self._results.empty()

    def visible_load_progress(self, *, world: WorldState, eye: Vec3, render_distance_chunks: int) -> tuple[int, int]:
        world_token = self._world_token(world)
        center = self._center_chunk(eye)
        rd = clamp_render_distance_chunks(int(render_distance_chunks))
        cache_key = (int(world_token), int(id(world)), int(world.revision), center, int(rd))

        if cache_key != self._visible_cache_key:
            existing = {normalize_chunk_key(ck) for ck in world.existing_chunk_keys()}
            if not existing:
                self._visible_cache_key = cache_key
                self._visible_cache_chunks = ()
                return (0, 0)
            self._visible_cache_key = cache_key
            self._visible_cache_chunks = tuple(self._needed_chunks(existing, center, rd, y_pad=1))

        visible = self._visible_cache_chunks

        ready = 0
        total = 0
        for ck in visible:
            chunk_revision = int(world.chunk_mesh_revision(ck))
            if chunk_revision <= 0:
                continue
            total += 1
            if int(world_token) == int(self._active_world_token if self._active_world_token is not None else world_token) and int(self._resident_rev.get(ck, -1)) == int(chunk_revision):
                ready += 1
        return (int(ready), int(total))

    def visible_chunks_ready(self, *, world: WorldState, eye: Vec3, render_distance_chunks: int) -> bool:
        ready, total = self.visible_load_progress(world=world, eye=eye, render_distance_chunks=int(render_distance_chunks))
        return int(ready) >= int(total)

    def upload_if_needed(self, *, world: WorldState, renderer: GLRenderer, eye: Vec3, render_distance_chunks: int) -> None:
        self._active_world_token = self._world_token(world)
        self._drain_results(renderer, world=world)

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

        self._drain_results(renderer, world=world)

    def prewarm_cache(self, *, world: WorldState, renderer: GLRenderer, eye: Vec3, render_distance_chunks: int) -> None:
        existing = {normalize_chunk_key(ck) for ck in world.existing_chunk_keys()}
        if not existing:
            return

        center = self._center_chunk(eye)
        rd = clamp_render_distance_chunks(int(render_distance_chunks))

        visible = self._needed_chunks(existing, center, rd, y_pad=1)
        prefetch = self._needed_chunks(existing, center, rd + 1, y_pad=1)

        self._schedule_chunks_if_stale(world=world, renderer=renderer, chunks=visible)
        self._schedule_chunks_if_stale(world=world, renderer=renderer, chunks=prefetch)
