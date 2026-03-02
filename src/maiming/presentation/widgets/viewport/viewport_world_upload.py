# FILE: src/maiming/presentation/widgets/viewport/viewport_world_upload.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import math
import queue
import time
from concurrent.futures import ThreadPoolExecutor, Future

import numpy as np

from maiming.core.math.vec3 import Vec3
from maiming.domain.world.chunking import ChunkKey, chunk_key
from maiming.domain.world.world_state import WorldState
from maiming.infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from maiming.infrastructure.rendering.opengl.facade.world_mesh_builder import build_chunk_mesh_cpu

@dataclass(frozen=True)
class _BuildResult:
    chunk: ChunkKey
    chunk_rev: int
    faces: list[np.ndarray]
    casters: np.ndarray

class WorldUploadTracker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="WorldMeshBuild")
        self._pending: Dict[ChunkKey, Future] = {}

        self._want_rev: Dict[ChunkKey, int] = {}
        self._resident_rev: Dict[ChunkKey, int] = {}

        self._results: "queue.Queue[_BuildResult]" = queue.Queue()

    def _drain_results(self, renderer: GLRenderer) -> None:
        while True:
            try:
                r = self._results.get_nowait()
            except queue.Empty:
                break

            want = self._want_rev.get(r.chunk)
            if want is None or int(want) != int(r.chunk_rev):
                continue

            renderer.submit_chunk(
                chunk_key=r.chunk,
                world_revision=int(r.chunk_rev),
                faces=r.faces,
                casters=r.casters,
            )
            self._resident_rev[r.chunk] = int(r.chunk_rev)

    @staticmethod
    def _center_chunk(eye: Vec3) -> ChunkKey:
        bx = int(math.floor(float(eye.x)))
        by = int(math.floor(float(eye.y)))
        bz = int(math.floor(float(eye.z)))
        return chunk_key(bx, by, bz)

    @staticmethod
    def _needed_chunks(existing: set[ChunkKey], center: ChunkKey, rd: int, y_pad: int = 1) -> list[ChunkKey]:
        cx, cy, cz = (int(center[0]), int(center[1]), int(center[2]))
        r = int(max(0, rd))

        out: list[ChunkKey] = []
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                for dy in range(-int(y_pad), int(y_pad) + 1):
                    ck = (cx + dx, cy + dy, cz + dz)
                    if ck in existing:
                        out.append(ck)
        out.sort(key=lambda k: (abs(int(k[0]) - cx) + abs(int(k[2]) - cz), abs(int(k[1]) - cy)))
        return out

    def bootstrap_resident(
        self,
        *,
        world: WorldState,
        renderer: GLRenderer,
        eye: Vec3,
        render_distance_chunks: int,
    ) -> None:
        tools = renderer.world_build_tools()
        if tools is None:
            return
        uv_lookup, def_lookup = tools

        existing = world.existing_chunk_keys()
        center = self._center_chunk(eye)
        rd = int(max(2, min(16, int(render_distance_chunks))))
        need = self._needed_chunks(existing, center, rd, y_pad=1)

        for ck in need:
            cr = int(world.chunk_mesh_revision(ck))
            if cr <= 0:
                continue
            if int(self._resident_rev.get(ck, -1)) == int(cr):
                continue

            blocks_local, state_at = world.snapshot_for_chunk_build(ck)

            def get_state(x: int, y: int, z: int) -> str | None:
                return state_at.get((int(x), int(y), int(z)))

            faces, casters = build_chunk_mesh_cpu(
                blocks=blocks_local,
                get_state=get_state,
                uv_lookup=uv_lookup,
                def_lookup=def_lookup,
            )
            renderer.submit_chunk(chunk_key=ck, world_revision=int(cr), faces=faces, casters=casters)
            self._resident_rev[ck] = int(cr)

    def _schedule_build(
        self,
        *,
        world: WorldState,
        renderer: GLRenderer,
        ck: ChunkKey,
        chunk_rev: int,
    ) -> None:
        tools = renderer.world_build_tools()
        if tools is None:
            return
        uv_lookup, def_lookup = tools

        if int(chunk_rev) <= 0:
            return

        f = self._pending.get(ck)
        if f is not None and (not f.done()):
            return

        self._want_rev[ck] = int(chunk_rev)

        blocks_local, state_at = world.snapshot_for_chunk_build(ck)

        def get_state(x: int, y: int, z: int) -> str | None:
            return state_at.get((int(x), int(y), int(z)))

        def _task(chunk_key_local: ChunkKey, rev_local: int, blocks_local_in: list[tuple[int, int, int, str]]):
            faces, casters = build_chunk_mesh_cpu(
                blocks=blocks_local_in,
                get_state=get_state,
                uv_lookup=uv_lookup,
                def_lookup=def_lookup,
            )
            return _BuildResult(chunk=chunk_key_local, chunk_rev=int(rev_local), faces=faces, casters=casters)

        fut = self._executor.submit(_task, ck, int(chunk_rev), blocks_local)

        def _on_done(done_fut: Future):
            try:
                res = done_fut.result()
            except Exception:
                return
            self._results.put(res)

        fut.add_done_callback(_on_done)
        self._pending[ck] = fut

    def upload_if_needed(
        self,
        *,
        world: WorldState,
        renderer: GLRenderer,
        eye: Vec3,
        render_distance_chunks: int,
    ) -> None:
        self._drain_results(renderer)

        existing = world.existing_chunk_keys()
        if not existing:
            return

        center = self._center_chunk(eye)
        rd = int(max(2, min(16, int(render_distance_chunks))))

        visible = self._needed_chunks(existing, center, rd, y_pad=1)
        prefetch = self._needed_chunks(existing, center, rd + 2, y_pad=1)

        dirty_map = world.consume_dirty_chunks_with_rev()
        for ck, cr in dirty_map.items():
            if ck in existing:
                self._schedule_build(world=world, renderer=renderer, ck=ck, chunk_rev=int(cr))

        for ck in visible:
            cr = int(world.chunk_mesh_revision(ck))
            if cr <= 0:
                continue
            if int(self._resident_rev.get(ck, -1)) != int(cr):
                self._schedule_build(world=world, renderer=renderer, ck=ck, chunk_rev=int(cr))

        for ck in prefetch:
            cr = int(world.chunk_mesh_revision(ck))
            if cr <= 0:
                continue
            if int(self._resident_rev.get(ck, -1)) != int(cr):
                self._schedule_build(world=world, renderer=renderer, ck=ck, chunk_rev=int(cr))

        self._drain_results(renderer)

        t0 = time.perf_counter()
        budget_s = 0.0035

        tools = renderer.world_build_tools()
        if tools is None:
            return
        uv_lookup, def_lookup = tools

        for ck in visible:
            cr = int(world.chunk_mesh_revision(ck))
            if cr <= 0:
                continue
            if int(self._resident_rev.get(ck, -1)) == int(cr):
                continue
            if (time.perf_counter() - t0) > budget_s:
                break

            blocks_local, state_at = world.snapshot_for_chunk_build(ck)

            def get_state(x: int, y: int, z: int) -> str | None:
                return state_at.get((int(x), int(y), int(z)))

            faces, casters = build_chunk_mesh_cpu(
                blocks=blocks_local,
                get_state=get_state,
                uv_lookup=uv_lookup,
                def_lookup=def_lookup,
            )
            renderer.submit_chunk(chunk_key=ck, world_revision=int(cr), faces=faces, casters=casters)
            self._resident_rev[ck] = int(cr)