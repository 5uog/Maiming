# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import threading

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Tuple

from ..math.chunking.chunk_grid import ChunkKey, chunk_key, neighbor_chunk_keys_for_cell

BlockKey = Tuple[int, int, int]
ColumnKey = Tuple[int, int]

@dataclass
class WorldState:
    blocks: Dict[BlockKey, str]
    revision: int = 0

    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    _dirty_chunks: set[ChunkKey] = field(default_factory=set, init=False, repr=False)
    _chunk_index: Dict[ChunkKey, set[BlockKey]] = field(default_factory=dict, init=False, repr=False)
    _column_index: Dict[ColumnKey, set[int]] = field(default_factory=dict, init=False, repr=False)

    _chunk_mesh_rev: Dict[ChunkKey, int] = field(default_factory=dict, init=False, repr=False)
    _gravity_dirty_columns: Dict[ColumnKey, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        with self._lock:
            self._rebuild_indexes_locked()
            self._reset_mesh_tracking_locked()
            self._reset_gravity_tracking_locked()

    def _rebuild_indexes_locked(self) -> None:
        self._chunk_index.clear()
        self._column_index.clear()
        for k in self.blocks.keys():
            kk = (int(k[0]), int(k[1]), int(k[2]))
            ck = chunk_key(int(kk[0]), int(kk[1]), int(kk[2]))
            chunk_members = self._chunk_index.get(ck)
            if chunk_members is None:
                chunk_members = set()
                self._chunk_index[ck] = chunk_members
            chunk_members.add(kk)

            column_key = (int(kk[0]), int(kk[2]))
            column_members = self._column_index.get(column_key)
            if column_members is None:
                column_members = set()
                self._column_index[column_key] = column_members
            column_members.add(int(kk[1]))

    def _reset_mesh_tracking_locked(self) -> None:
        self._chunk_mesh_rev.clear()
        for ck in self._chunk_index.keys():
            self._chunk_mesh_rev[ck] = 1
        self._dirty_chunks = set(self._chunk_index.keys())

    def _reset_gravity_tracking_locked(self) -> None:
        self._gravity_dirty_columns.clear()
        for (x, z), ys in self._column_index.items():
            if not ys:
                continue
            self._gravity_dirty_columns[(int(x), int(z))] = int(min(int(y) for y in ys))

    def existing_chunk_keys(self) -> set[ChunkKey]:
        with self._lock:
            return set(self._chunk_index.keys())

    def chunk_mesh_revision(self, ck: ChunkKey) -> int:
        with self._lock:
            return int(self._chunk_mesh_rev.get((int(ck[0]), int(ck[1]), int(ck[2])), 0))

    def consume_dirty_chunks(self) -> set[ChunkKey]:
        with self._lock:
            out = set(self._dirty_chunks)
            self._dirty_chunks.clear()
            return out

    def consume_dirty_chunks_with_rev(self) -> Dict[ChunkKey, int]:
        with self._lock:
            out: Dict[ChunkKey, int] = {}
            for ck in self._dirty_chunks:
                out[ck] = int(self._chunk_mesh_rev.get(ck, 0))
            self._dirty_chunks.clear()
            return out

    def consume_pending_gravity_columns(self) -> Dict[ColumnKey, int]:
        with self._lock:
            out = dict(self._gravity_dirty_columns)
            self._gravity_dirty_columns.clear()
            return out

    def snapshot_blocks(self) -> Dict[BlockKey, str]:
        with self._lock:
            return dict(self.blocks)

    def snapshot_column(self, x: int, z: int) -> Dict[int, str]:
        cx = int(x)
        cz = int(z)
        with self._lock:
            ys = self._column_index.get((int(cx), int(cz)))
            if not ys:
                return {}
            return {int(y): str(self.blocks[(int(cx), int(y), int(cz))]) for y in ys if (int(cx), int(y), int(cz)) in self.blocks}

    def column_y_values(self, x: int, z: int) -> tuple[int, ...]:
        with self._lock:
            ys = self._column_index.get((int(x), int(z)))
            if not ys:
                return ()
            return tuple(sorted(int(y) for y in ys))

    def _index_add(self, k: BlockKey) -> None:
        ck = chunk_key(int(k[0]), int(k[1]), int(k[2]))
        chunk_members = self._chunk_index.get(ck)
        if chunk_members is None:
            chunk_members = set()
            self._chunk_index[ck] = chunk_members
        chunk_members.add((int(k[0]), int(k[1]), int(k[2])))

        column_key = (int(k[0]), int(k[2]))
        column_members = self._column_index.get(column_key)
        if column_members is None:
            column_members = set()
            self._column_index[column_key] = column_members
        column_members.add(int(k[1]))

        if ck not in self._chunk_mesh_rev:
            self._chunk_mesh_rev[ck] = 1

    def _index_remove(self, k: BlockKey) -> None:
        ck = chunk_key(int(k[0]), int(k[1]), int(k[2]))
        chunk_members = self._chunk_index.get(ck)
        if chunk_members is not None:
            chunk_members.discard((int(k[0]), int(k[1]), int(k[2])))
            if not chunk_members:
                try:
                    del self._chunk_index[ck]
                except KeyError:
                    pass
                self._chunk_mesh_rev.pop(ck, None)

        column_key = (int(k[0]), int(k[2]))
        column_members = self._column_index.get(column_key)
        if column_members is not None:
            column_members.discard(int(k[1]))
            if not column_members:
                try:
                    del self._column_index[column_key]
                except KeyError:
                    pass

    def _mark_chunks_dirty(self, keys: Iterable[ChunkKey]) -> None:
        for ck0 in keys:
            ck = (int(ck0[0]), int(ck0[1]), int(ck0[2]))
            cur = int(self._chunk_mesh_rev.get(ck, 0))
            nxt = 1 if cur <= 0 else (cur + 1)
            self._chunk_mesh_rev[ck] = int(nxt)
            self._dirty_chunks.add(ck)

    def _mark_gravity_dirty_cell(self, x: int, y: int, z: int) -> None:
        column_key = (int(x), int(z))
        current = self._gravity_dirty_columns.get(column_key)
        if current is None:
            self._gravity_dirty_columns[column_key] = int(y)
            return
        self._gravity_dirty_columns[column_key] = min(int(current), int(y))

    def _mark_gravity_dirty_cells(self, cells: Iterable[BlockKey]) -> None:
        for x, y, z in cells:
            self._mark_gravity_dirty_cell(int(x), int(y), int(z))

    def set_block(self, x: int, y: int, z: int, block_id: str) -> None:
        k = (int(x), int(y), int(z))
        value = str(block_id)
        with self._lock:
            prev = self.blocks.get(k)
            if prev == value:
                return

            existed = k in self.blocks
            self.blocks[k] = value
            if not existed:
                self._index_add(k)

            self.revision += 1
            self._mark_chunks_dirty(neighbor_chunk_keys_for_cell(int(x), int(y), int(z)))
            self._mark_gravity_dirty_cell(int(x), int(y), int(z))
            self._mark_gravity_dirty_cell(int(x), int(y) + 1, int(z))

    def remove_block(self, x: int, y: int, z: int) -> None:
        k = (int(x), int(y), int(z))
        with self._lock:
            if k not in self.blocks:
                return

            del self.blocks[k]
            self._index_remove(k)

            self.revision += 1
            self._mark_chunks_dirty(neighbor_chunk_keys_for_cell(int(x), int(y), int(z)))
            self._mark_gravity_dirty_cell(int(x), int(y), int(z))
            self._mark_gravity_dirty_cell(int(x), int(y) + 1, int(z))

    def set_blocks_bulk(self, *, updates: Dict[BlockKey, str] | None = None, removals: Iterable[BlockKey] = ()) -> None:
        upd_in = updates or {}

        norm_updates: Dict[BlockKey, str] = {}
        for k0, v0 in upd_in.items():
            kk = (int(k0[0]), int(k0[1]), int(k0[2]))
            norm_updates[kk] = str(v0)

        norm_removals: set[BlockKey] = set()
        for k0 in removals:
            kk = (int(k0[0]), int(k0[1]), int(k0[2]))
            if kk in norm_updates:
                continue
            norm_removals.add(kk)

        if not norm_updates and not norm_removals:
            return

        dirty_keys: set[ChunkKey] = set()
        gravity_cells: set[BlockKey] = set()
        changed = False

        with self._lock:
            for k in norm_removals:
                if k not in self.blocks:
                    continue

                del self.blocks[k]
                self._index_remove(k)
                dirty_keys.update(neighbor_chunk_keys_for_cell(int(k[0]), int(k[1]), int(k[2])))
                gravity_cells.add((int(k[0]), int(k[1]), int(k[2])))
                gravity_cells.add((int(k[0]), int(k[1]) + 1, int(k[2])))
                changed = True

            for k, v in norm_updates.items():
                prev = self.blocks.get(k)
                if prev == str(v):
                    continue

                existed = k in self.blocks
                self.blocks[k] = str(v)
                if not existed:
                    self._index_add(k)

                dirty_keys.update(neighbor_chunk_keys_for_cell(int(k[0]), int(k[1]), int(k[2])))
                gravity_cells.add((int(k[0]), int(k[1]), int(k[2])))
                gravity_cells.add((int(k[0]), int(k[1]) + 1, int(k[2])))
                changed = True

            if not changed:
                return

            self.revision += 1
            self._mark_chunks_dirty(dirty_keys)
            self._mark_gravity_dirty_cells(gravity_cells)

    def iter_blocks(self) -> Iterable[tuple[int, int, int, str]]:
        with self._lock:
            items = list(self.blocks.items())
        for (x, y, z), bid in items:
            yield int(x), int(y), int(z), str(bid)

    def snapshot_for_chunk_build(self, target: ChunkKey) -> tuple[list[tuple[int, int, int, str]], Dict[BlockKey, str]]:
        cx, cy, cz = (int(target[0]), int(target[1]), int(target[2]))
        neigh: list[ChunkKey] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    neigh.append((cx + dx, cy + dy, cz + dz))

        with self._lock:
            state_at: Dict[BlockKey, str] = {}

            for ck in neigh:
                keys = self._chunk_index.get(ck)
                if not keys:
                    continue
                for k in keys:
                    s = self.blocks.get(k)
                    if s is None:
                        continue
                    state_at[(int(k[0]), int(k[1]), int(k[2]))] = str(s)

            blocks_local: list[tuple[int, int, int, str]] = []
            keys_t = self._chunk_index.get((cx, cy, cz))
            if keys_t:
                for k in keys_t:
                    s = state_at.get(k)
                    if s is None:
                        s2 = self.blocks.get(k)
                        if s2 is None:
                            continue
                        s = str(s2)
                        state_at[(int(k[0]), int(k[1]), int(k[2]))] = s
                    blocks_local.append((int(k[0]), int(k[1]), int(k[2]), str(s)))

        return blocks_local, state_at

    def to_persisted_dict(self) -> dict[str, Any]:
        with self._lock:
            items: list[list[Any]] = []
            for (x, y, z), s in self.blocks.items():
                items.append([int(x), int(y), int(z), str(s)])
            return {"revision": int(self.revision), "blocks": items}

    @staticmethod
    def from_persisted_dict(d: dict[str, Any]) -> "WorldState":
        rev = d.get("revision", 0)
        try:
            revision = int(rev)
        except Exception:
            revision = 0

        out: Dict[BlockKey, str] = {}
        raw = d.get("blocks", [])
        if isinstance(raw, list):
            for it in raw:
                if not isinstance(it, list) or len(it) != 4:
                    continue
                try:
                    x = int(it[0])
                    y = int(it[1])
                    z = int(it[2])
                    s = str(it[3])
                except Exception:
                    continue
                out[(x, y, z)] = s

        return WorldState(blocks=out, revision=int(max(0, revision)))

    def replace_all(self, *, blocks: Dict[BlockKey, str], revision: int) -> None:
        with self._lock:
            self.blocks.clear()
            for k, v in blocks.items():
                kk = (int(k[0]), int(k[1]), int(k[2]))
                self.blocks[kk] = str(v)

            self.revision = int(max(0, int(revision)))
            self._rebuild_indexes_locked()
            self._reset_mesh_tracking_locked()
            self._reset_gravity_tracking_locked()