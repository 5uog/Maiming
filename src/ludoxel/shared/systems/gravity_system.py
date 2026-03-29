# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..blocks.models.api import collision_aabbs_for_block
from ..blocks.models.api import has_full_top_support_for_block
from ..blocks.registry.block_registry import BlockRegistry
from ..blocks.state.state_codec import parse_state
from ..blocks.state.state_values import slab_type_value
from ..blocks.state.state_view import def_from_state, world_state_at
from ..blocks.structure.structural_rules import is_fence, is_fence_gate, is_slab, is_stairs, is_wall
from ..blocks.structure.connectivity import collect_structural_neighbor_updates
from ..world.entities.player_entity import PlayerEntity
from ..world.world_state import BlockKey, WorldState

GRAVITY_AFFECTED_TAG = "gravity_affected"
_FALLING_BLOCK_TICK_S = 1.0 / 20.0
_FALLING_BLOCK_GRAVITY_PER_TICK = 0.04
_FALLING_BLOCK_DRAG = 0.98
_FALLING_BLOCK_EPS = 1e-6


def _overlay_state_getter(world: WorldState, *, updates: dict[BlockKey, str], removals: set[BlockKey]):

    def get_state(x: int, y: int, z: int) -> str | None:
        key = (int(x), int(y), int(z))
        if key in removals:
            return None
        if key in updates:
            return str(updates[key])
        return world_state_at(world, int(x), int(y), int(z))

    return get_state


@dataclass(frozen=True)
class GravityStepResult:
    moved_cells: tuple[BlockKey, ...] = ()
    broken_blocks: tuple["GravityBrokenBlock", ...] = ()


@dataclass(frozen=True)
class GravityBrokenBlock:
    state_str: str
    cell: BlockKey


@dataclass(frozen=True)
class FallingBlockRenderSample:
    state_str: str
    x: float
    y: float
    z: float


@dataclass
class _ActiveFallingBlock:
    block_id: int
    state_str: str
    x: int
    z: int
    y: float
    prev_y: float
    velocity_y_per_tick: float = 0.0


@dataclass(frozen=True)
class _LandingTarget:
    mode: str
    support_y: float


@dataclass
class GravitySystem:
    block_registry: BlockRegistry

    _active_blocks: dict[int, _ActiveFallingBlock] = field(default_factory=dict, init=False, repr=False)
    _tick_accum_s: float = field(default=0.0, init=False, repr=False)
    _next_block_id: int = field(default=1, init=False, repr=False)

    def _is_gravity_affected(self, state_str: str | None) -> bool:
        defn = def_from_state(state_str, self.block_registry)
        if defn is None:
            return False
        return bool(defn.is_family("block") and defn.has_tag(GRAVITY_AFFECTED_TAG))

    def _has_top_support(self, world: WorldState, *, x: int, y: int, z: int, state_str: str, updates: dict[BlockKey, str], removals: set[BlockKey]) -> bool:
        get_state = _overlay_state_getter(world, updates=updates, removals=removals)
        return bool(has_full_top_support_for_block(str(state_str), get_state, self.block_registry.get, int(x), int(y), int(z)))

    def _landing_target_for_support(self, world: WorldState, *, x: int, y: int, z: int, state_str: str, updates: dict[BlockKey, str], removals: set[BlockKey]) -> _LandingTarget | None:
        if self._has_top_support(world, x=int(x), y=int(y), z=int(z), state_str=str(state_str), updates=updates, removals=removals):
            return _LandingTarget(mode="land", support_y=float(int(y) + 1))

        defn = def_from_state(state_str, self.block_registry)
        if defn is None:
            return None

        _base, props = parse_state(str(state_str))

        if is_slab(defn):
            if slab_type_value(props) == "bottom":
                return _LandingTarget(mode="break", support_y=float(int(y)) + 0.5)
            return _LandingTarget(mode="land", support_y=float(int(y) + 1))

        if is_stairs(defn):
            return _LandingTarget(mode="land", support_y=float(int(y) + 1))

        if is_fence(defn) or is_fence_gate(defn) or is_wall(defn):
            return _LandingTarget(mode="land", support_y=float(int(y) + 1))

        return None

    def _spawn_active_block(self, *, state_str: str, x: int, y: int, z: int) -> None:
        block_id = int(self._next_block_id)
        self._next_block_id += 1
        self._active_blocks[block_id] = _ActiveFallingBlock(block_id=int(block_id), state_str=str(state_str), x=int(x), z=int(z), y=float(y), prev_y=float(y), velocity_y_per_tick=0.0)

    def _spawn_pending_blocks(self, world: WorldState) -> tuple[BlockKey, ...]:
        pending_columns = world.consume_pending_gravity_columns()
        if not pending_columns:
            return ()

        removals: set[BlockKey] = set()
        spawned_cells: set[BlockKey] = set()
        empty_updates: dict[BlockKey, str] = {}
        get_state = _overlay_state_getter(world, updates=empty_updates, removals=removals)

        for (x0, z0), min_y in sorted(pending_columns.items(), key=lambda item: (int(item[0][0]), int(item[0][1]), int(item[1]))):
            x = int(x0)
            z = int(z0)
            y_values = sorted(int(y) for y in world.snapshot_column(int(x), int(z)).keys())
            if not y_values:
                continue

            for y in y_values:
                if int(y) < int(min_y) - 1:
                    continue

                state_str = get_state(int(x), int(y), int(z))
                if not self._is_gravity_affected(state_str):
                    continue

                below_state = get_state(int(x), int(y - 1), int(z))
                landing_target = None if below_state is None else self._landing_target_for_support(world, x=int(x), y=int(y - 1), z=int(z), state_str=str(below_state), updates=empty_updates, removals=removals)
                if landing_target is not None and str(landing_target.mode) == "land":
                    continue

                src = (int(x), int(y), int(z))
                removals.add(src)
                spawned_cells.add(src)
                self._spawn_active_block(state_str=str(state_str), x=int(x), y=int(y), z=int(z))

        if not removals:
            return ()

        structural_updates = collect_structural_neighbor_updates(world, spawned_cells, block_registry=self.block_registry, overlay_updates=empty_updates, overlay_removals=removals)
        world.set_blocks_bulk(updates=structural_updates, removals=removals)
        return tuple(sorted(spawned_cells))

    def _landing_target(self, world: WorldState, *, x: int, z: int, ceiling_y: float, updates: dict[BlockKey, str], removals: set[BlockKey]) -> _LandingTarget | None:
        get_state = _overlay_state_getter(world, updates=updates, removals=removals)
        y_values = set(world.column_y_values(int(x), int(z)))
        for (ux, uy, uz) in updates.keys():
            if int(ux) == int(x) and int(uz) == int(z):
                y_values.add(int(uy))

        for y in sorted((int(value) for value in y_values), reverse=True):
            state_str = get_state(int(x), int(y), int(z))
            if state_str is None:
                continue

            landing_target = self._landing_target_for_support(world, x=int(x), y=int(y), z=int(z), state_str=str(state_str), updates=updates, removals=removals)
            if landing_target is None:
                continue
            if float(landing_target.support_y) > float(ceiling_y) + float(_FALLING_BLOCK_EPS):
                continue
            return landing_target

        return None

    def _player_intersects_landed_block(self, player: PlayerEntity, world: WorldState, *, cell: BlockKey, state_str: str, updates: dict[BlockKey, str], removals: set[BlockKey]) -> bool:
        player_aabb = player.aabb_at(player.position)
        get_state = _overlay_state_getter(world, updates=updates, removals=removals)
        px, py, pz = (int(cell[0]), int(cell[1]), int(cell[2]))
        for box in collision_aabbs_for_block(str(state_str), get_state, self.block_registry.get, int(px), int(py), int(pz)):
            if player_aabb.intersects(box):
                return True
        return False

    def _advance_active_blocks(self, world: WorldState, *, player: PlayerEntity | None=None) -> GravityStepResult:
        if not self._active_blocks:
            return GravityStepResult()

        landed_updates: dict[BlockKey, str] = {}
        landed_cells: set[BlockKey] = set()
        removals: set[BlockKey] = set()
        completed_ids: list[int] = []
        player_overlap_exemptions: set[BlockKey] = set()
        broken_blocks: list[GravityBrokenBlock] = []
        get_state = _overlay_state_getter(world, updates=landed_updates, removals=removals)

        for block in sorted(self._active_blocks.values(), key=lambda item: (float(item.y), int(item.x), int(item.z), int(item.block_id))):
            block.prev_y = float(block.y)
            next_velocity = (float(block.velocity_y_per_tick) - float(_FALLING_BLOCK_GRAVITY_PER_TICK)) * float(_FALLING_BLOCK_DRAG)
            next_y = float(block.y) + float(next_velocity)
            landing_target = self._landing_target(world, x=int(block.x), z=int(block.z), ceiling_y=float(block.y), updates=landed_updates, removals=removals)

            if landing_target is not None and float(next_y) <= float(landing_target.support_y) + float(_FALLING_BLOCK_EPS):
                if str(landing_target.mode) == "break":
                    broken_cell = (int(block.x), int(math.floor(float(block.y) + float(_FALLING_BLOCK_EPS))), int(block.z))
                    broken_blocks.append(GravityBrokenBlock(state_str=str(block.state_str), cell=broken_cell))
                    completed_ids.append(int(block.block_id))
                    continue

                dst_y = int(math.floor(float(landing_target.support_y) + float(_FALLING_BLOCK_EPS)))
                dst = (int(block.x), int(dst_y), int(block.z))
                if get_state(int(block.x), int(dst_y), int(block.z)) is None:
                    landed_updates[dst] = str(block.state_str)
                    landed_cells.add(dst)
                    if player is not None and self._player_intersects_landed_block(player, world, cell=dst, state_str=str(block.state_str), updates=landed_updates, removals=removals):
                        player_overlap_exemptions.add(dst)
                completed_ids.append(int(block.block_id))
                continue

            block.velocity_y_per_tick = float(next_velocity)
            block.y = float(next_y)

        for block_id in completed_ids:
            self._active_blocks.pop(int(block_id), None)

        if not landed_updates:
            return GravityStepResult(moved_cells=(), broken_blocks=tuple(broken_blocks))

        structural_updates = collect_structural_neighbor_updates(world, landed_cells, block_registry=self.block_registry, overlay_updates=landed_updates, overlay_removals=removals)
        final_updates = dict(landed_updates)
        final_updates.update(structural_updates)
        world.set_blocks_bulk(updates=final_updates, removals=removals)
        if player is not None and player_overlap_exemptions:
            merged = set(tuple((int(cell[0]), int(cell[1]), int(cell[2])) for cell in player.gravity_block_overlap_exemptions))
            merged.update((int(cell[0]), int(cell[1]), int(cell[2])) for cell in player_overlap_exemptions)
            player.gravity_block_overlap_exemptions = tuple(sorted(merged))
        return GravityStepResult(moved_cells=tuple(sorted(landed_cells)), broken_blocks=tuple(broken_blocks))

    def step(self, world: WorldState, dt: float, *, player: PlayerEntity | None=None) -> GravityStepResult:
        moved_cells: set[BlockKey] = set(self._spawn_pending_blocks(world))
        broken_blocks: list[GravityBrokenBlock] = []
        self._tick_accum_s = max(0.0, float(self._tick_accum_s) + max(0.0, float(dt)))

        while float(self._tick_accum_s) + float(_FALLING_BLOCK_EPS) >= float(_FALLING_BLOCK_TICK_S):
            self._tick_accum_s = max(0.0, float(self._tick_accum_s) - float(_FALLING_BLOCK_TICK_S))
            advance_result = self._advance_active_blocks(world, player=player)
            moved_cells.update(advance_result.moved_cells)
            broken_blocks.extend(advance_result.broken_blocks)

        return GravityStepResult(moved_cells=tuple(sorted(moved_cells)), broken_blocks=tuple(broken_blocks))

    def render_samples(self) -> tuple[FallingBlockRenderSample, ...]:
        if not self._active_blocks:
            return ()

        alpha = 0.0
        if float(_FALLING_BLOCK_TICK_S) > float(_FALLING_BLOCK_EPS):
            alpha = max(0.0, min(1.0, float(self._tick_accum_s) / float(_FALLING_BLOCK_TICK_S)))

        samples: list[FallingBlockRenderSample] = []
        for block in sorted(self._active_blocks.values(), key=lambda item: (int(item.x), float(item.y), int(item.z), int(item.block_id))):
            sample_y = float(block.prev_y) + (float(block.y) - float(block.prev_y)) * float(alpha)
            samples.append(FallingBlockRenderSample(state_str=str(block.state_str), x=float(block.x), y=float(sample_y), z=float(block.z)))

        return tuple(samples)

    def snapshot_blocks_for_persistence(self, world: WorldState) -> dict[BlockKey, str]:
        snapshot = world.snapshot_blocks()
        for block in self._active_blocks.values():
            y = int(math.floor(float(block.y) + float(_FALLING_BLOCK_EPS)))
            snapshot[(int(block.x), int(y), int(block.z))] = str(block.state_str)
        return snapshot
