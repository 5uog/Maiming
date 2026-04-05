# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math

from ....shared.blocks.models.api import has_full_top_support_for_block
from ....shared.blocks.registry.default_registry import create_default_registry
from ....shared.math.vec3 import Vec3
from ....shared.systems.collision_system import _any_intersection
from ....shared.world.entities.player_entity import PlayerEntity
from ....shared.world.world_state import WorldState
from ..ai_player_types import AiRoutePoint
from ..state.session_settings import SessionSettings

_PLAN_MAX_SUPPORT_Y_DELTA = 1
_PLAN_PARKOUR_SEARCH_CAP = 8
_PLAN_PARKOUR_SAMPLE_COUNT = 5
_PLAN_DROP_SEARCH_DEPTH = 4
_PLAN_VISIT_LIMIT_MIN = 1024
_PLAN_VISIT_LIMIT_MAX = 4096
_PLAN_TARGET_SUPPORT_SEARCH_RADIUS = 6

_BLOCK_REGISTRY = None


def _block_registry():
    global _BLOCK_REGISTRY
    if _BLOCK_REGISTRY is None:
        _BLOCK_REGISTRY = create_default_registry()
    return _BLOCK_REGISTRY


@dataclass(frozen=True)
class AiRoutePlanStep:
    support_cell: tuple[int, int, int]
    placement_anchor: tuple[int, int, int] | None = None
    jump_required: bool = False
    jump_span: int = 1


@dataclass(frozen=True)
class AiRoutePlanRequest:
    generation: int
    actor_id: str
    world_revision: int
    world_blocks: tuple[tuple[int, int, int, str], ...]
    settings: SessionSettings
    start_support: tuple[int, int, int]
    route_points: tuple[AiRoutePoint, ...]
    route_target_index: int
    can_place_blocks: bool
    blocked_edges: tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...] = ()
    avoid_support_cells: tuple[tuple[int, int, int], ...] = ()
    search_radius: int = 18


@dataclass(frozen=True)
class AiRoutePlanResult:
    generation: int
    actor_id: str
    world_revision: int
    start_support: tuple[int, int, int]
    route_target_index: int
    success: bool
    path: tuple[AiRoutePlanStep, ...] = ()


@dataclass(frozen=True)
class _SupportTransition:
    target_cell: tuple[int, int, int]
    placement_anchor: tuple[int, int, int] | None = None
    jump_required: bool = False
    jump_span: int = 1
    travel_cost: float = 1.25


@dataclass(frozen=True)
class _PlannerContext:
    world: WorldState
    settings: SessionSettings
    player: PlayerEntity
    can_place_blocks: bool
    blocked_edges: frozenset[tuple[tuple[int, int, int], tuple[int, int, int]]]
    avoid_support_cells: frozenset[tuple[int, int, int]]


def _support_cell_center(support_cell: tuple[int, int, int]) -> Vec3:
    return Vec3(float(support_cell[0]) + 0.5, float(support_cell[1]) + 1.0, float(support_cell[2]) + 0.5)


def _support_cell_from_point(point: Vec3) -> tuple[int, int, int]:
    return (int(math.floor(float(point.x))), int(math.floor(float(point.y) - 0.01)), int(math.floor(float(point.z))))


def _horizontal_transition_distance(from_cell: tuple[int, int, int], to_cell: tuple[int, int, int]) -> float:
    return float(math.hypot(float(int(to_cell[0]) - int(from_cell[0])), float(int(to_cell[2]) - int(from_cell[2]))))


def _state_at(ctx: _PlannerContext, cell: tuple[int, int, int]) -> str | None:
    return ctx.world.blocks.get((int(cell[0]), int(cell[1]), int(cell[2])))


def _cell_has_full_top_support(ctx: _PlannerContext, cell: tuple[int, int, int]) -> bool:
    state_str = _state_at(ctx, cell)
    if state_str is None:
        return False
    registry = _block_registry()
    return bool(has_full_top_support_for_block(str(state_str), lambda x, y, z: ctx.world.blocks.get((int(x), int(y), int(z))), registry.get, int(cell[0]), int(cell[1]), int(cell[2])))


def _nav_cell_empty(ctx: _PlannerContext, cell: tuple[int, int, int]) -> bool:
    return _state_at(ctx, cell) is None


def _nav_headroom_clear(ctx: _PlannerContext, support_cell: tuple[int, int, int]) -> bool:
    x, y, z = (int(support_cell[0]), int(support_cell[1]), int(support_cell[2]))
    return bool(_nav_cell_empty(ctx, (int(x), int(y) + 1, int(z))) and _nav_cell_empty(ctx, (int(x), int(y) + 2, int(z))))


def _player_clear_at(ctx: _PlannerContext, *, position: Vec3) -> bool:
    probe_aabb = ctx.player.aabb_at(Vec3(float(position.x), float(position.y), float(position.z)))
    return not bool(_any_intersection(ctx.world, probe_aabb, ctx.settings.collision, block_registry=_block_registry()))


def _standable_support_cell(ctx: _PlannerContext, support_cell: tuple[int, int, int]) -> bool:
    if not bool(_cell_has_full_top_support(ctx, tuple(int(value) for value in support_cell))):
        return False
    return bool(_nav_headroom_clear(ctx, tuple(int(value) for value in support_cell)))


def _transition_clear_between_support_cells(ctx: _PlannerContext, *, from_cell: tuple[int, int, int], to_cell: tuple[int, int, int]) -> bool:
    src = tuple(int(value) for value in from_cell)
    dst = tuple(int(value) for value in to_cell)
    dx = int(dst[0]) - int(src[0])
    dz = int(dst[2]) - int(src[2])
    horizontal_span = max(abs(int(dx)), abs(int(dz)))
    if int(horizontal_span) != 1 or (int(dx) == 0 and int(dz) == 0):
        return False
    if abs(int(dst[1]) - int(src[1])) > int(_PLAN_MAX_SUPPORT_Y_DELTA):
        return False
    if (not bool(_nav_headroom_clear(ctx, src))) or (not bool(_nav_headroom_clear(ctx, dst))):
        return False
    start = _support_cell_center(src)
    end = _support_cell_center(dst)
    probe_y = float(max(float(start.y), float(end.y)))
    sample_count = 6 if (int(dx) != 0 and int(dz) != 0) else 4
    for sample_index in range(1, int(sample_count)):
        ratio = float(sample_index) / float(sample_count)
        probe = Vec3(float(start.x) + (float(end.x) - float(start.x)) * float(ratio), float(probe_y), float(start.z) + (float(end.z) - float(start.z)) * float(ratio))
        if not bool(_player_clear_at(ctx, position=probe)):
            return False
    return True


def _parkour_jump_reach_blocks(ctx: _PlannerContext) -> float:
    movement = ctx.settings.movement
    gravity = max(1e-6, float(movement.gravity))
    jump_v0 = max(0.0, float(movement.jump_v0))
    launch_speed = max(float(movement.walk_speed), float(movement.sprint_speed)) + max(0.0, float(movement.sprint_jump_boost))
    flight_time = (2.0 * float(jump_v0)) / float(gravity)
    return max(0.0, float(launch_speed) * float(flight_time))


def _max_parkour_jump_span(ctx: _PlannerContext) -> int:
    reach_blocks = _parkour_jump_reach_blocks(ctx)
    return max(2, min(int(_PLAN_PARKOUR_SEARCH_CAP), int(math.floor(float(reach_blocks) + 0.25))))


def _jump_arc_clear(ctx: _PlannerContext, *, from_cell: tuple[int, int, int], to_cell: tuple[int, int, int]) -> bool:
    start = _support_cell_center(tuple(int(value) for value in from_cell))
    end = _support_cell_center(tuple(int(value) for value in to_cell))
    delta = end - start
    horizontal_distance = float(_horizontal_transition_distance(tuple(int(value) for value in from_cell), tuple(int(value) for value in to_cell)))
    if float(horizontal_distance) <= 1.05:
        return False
    apex = 0.95 + max(0.0, float(horizontal_distance - 2.0)) * 0.22 + max(0.0, float(to_cell[1] - from_cell[1])) * 0.30
    sample_count = max(3, int(max(float(_PLAN_PARKOUR_SAMPLE_COUNT), math.ceil(float(horizontal_distance) * 2.0))))
    for sample_index in range(1, int(sample_count) + 1):
        ratio = float(sample_index) / float(sample_count)
        base = start + delta * float(ratio)
        arc_y = float(4.0 * ratio * (1.0 - ratio) * apex)
        probe = Vec3(float(base.x), float(base.y) + float(arc_y), float(base.z))
        if not bool(_player_clear_at(ctx, position=probe)):
            return False
    return True


def _can_place_support_block(ctx: _PlannerContext, *, anchor_cell: tuple[int, int, int], target_cell: tuple[int, int, int]) -> bool:
    if not bool(ctx.can_place_blocks):
        return False
    if _state_at(ctx, tuple(int(value) for value in anchor_cell)) is None:
        return False
    if _state_at(ctx, tuple(int(value) for value in target_cell)) is not None:
        return False
    return bool(_nav_headroom_clear(ctx, tuple(int(value) for value in target_cell)))


def _parkour_jump_transition(ctx: _PlannerContext, *, support_cell: tuple[int, int, int], delta_x: int, delta_z: int) -> _SupportTransition | None:
    horizontal_span = max(abs(int(delta_x)), abs(int(delta_z)))
    horizontal_distance = float(math.hypot(float(delta_x), float(delta_z)))
    if int(horizontal_span) <= 1 or int(horizontal_span) > int(_max_parkour_jump_span(ctx)):
        return None
    if float(horizontal_distance) > float(_parkour_jump_reach_blocks(ctx)) + 0.25:
        return None
    x, y, z = (int(support_cell[0]), int(support_cell[1]), int(support_cell[2]))
    for landing_dy in (0, -1, 1, -2, -3):
        candidate = (int(x) + int(delta_x), int(y) + int(landing_dy), int(z) + int(delta_z))
        if not bool(_standable_support_cell(ctx, candidate)):
            continue
        if not bool(_jump_arc_clear(ctx, from_cell=tuple(int(value) for value in support_cell), to_cell=candidate)):
            continue
        travel_cost = 1.10 + float(horizontal_distance) * 1.55 + abs(float(landing_dy)) * 0.75
        return _SupportTransition(target_cell=candidate, placement_anchor=None, jump_required=True, jump_span=int(horizontal_span), travel_cost=float(travel_cost))
    return None


def _drop_arc_clear(ctx: _PlannerContext, *, from_cell: tuple[int, int, int], to_cell: tuple[int, int, int]) -> bool:
    start = _support_cell_center(tuple(int(value) for value in from_cell))
    end = _support_cell_center(tuple(int(value) for value in to_cell))
    delta = end - start
    sample_count = max(4, int(abs(int(to_cell[1]) - int(from_cell[1]))) * 2 + 2)
    for sample_index in range(1, int(sample_count) + 1):
        ratio = float(sample_index) / float(sample_count)
        lift = 0.24 * (1.0 - float(ratio))
        probe = Vec3(float(start.x) + float(delta.x) * float(ratio), float(start.y) + float(delta.y) * float(ratio) + float(lift), float(start.z) + float(delta.z) * float(ratio))
        if not bool(_player_clear_at(ctx, position=probe)):
            return False
    return True


def _drop_transition(ctx: _PlannerContext, *, support_cell: tuple[int, int, int], delta_x: int, delta_z: int) -> _SupportTransition | None:
    horizontal_span = max(abs(int(delta_x)), abs(int(delta_z)))
    if int(horizontal_span) != 1 or (int(delta_x) == 0 and int(delta_z) == 0):
        return None
    x, y, z = (int(support_cell[0]), int(support_cell[1]), int(support_cell[2]))
    for drop_dy in range(-1, -int(_PLAN_DROP_SEARCH_DEPTH) - 1, -1):
        candidate = (int(x) + int(delta_x), int(y) + int(drop_dy), int(z) + int(delta_z))
        if not bool(_standable_support_cell(ctx, candidate)):
            continue
        if not bool(_drop_arc_clear(ctx, from_cell=tuple(int(value) for value in support_cell), to_cell=candidate)):
            continue
        travel_cost = float(math.hypot(float(delta_x), float(delta_z))) + 0.05 + abs(float(drop_dy)) * 0.30
        return _SupportTransition(target_cell=candidate, placement_anchor=None, jump_required=False, jump_span=1, travel_cost=float(travel_cost))
    return None


def _nearest_standable_support_cell(ctx: _PlannerContext, preferred_cell: tuple[int, int, int]) -> tuple[int, int, int] | None:
    base = tuple(int(value) for value in preferred_cell)
    if bool(_standable_support_cell(ctx, base)):
        return base
    for radius in range(1, int(_PLAN_TARGET_SUPPORT_SEARCH_RADIUS) + 1):
        for dx in range(-int(radius), int(radius) + 1):
            for dz in range(-int(radius), int(radius) + 1):
                for dy in range(-3, int(_PLAN_MAX_SUPPORT_Y_DELTA) + 1):
                    candidate = (int(base[0]) + int(dx), int(base[1]) + int(dy), int(base[2]) + int(dz))
                    if bool(_standable_support_cell(ctx, candidate)):
                        return candidate
    return None


def _neighbor_support_transitions(ctx: _PlannerContext, support_cell: tuple[int, int, int], *, target_cell: tuple[int, int, int] | None=None) -> tuple[_SupportTransition, ...]:
    x, y, z = (int(support_cell[0]), int(support_cell[1]), int(support_cell[2]))
    candidates: list[_SupportTransition] = []
    avoid_cells = set(tuple(int(value) for value in cell) for cell in ctx.avoid_support_cells)
    blocked_edges = set(ctx.blocked_edges)
    seen_targets: set[tuple[int, int, int]] = set()
    target_vec_x = 0 if target_cell is None else int(target_cell[0]) - int(x)
    target_vec_z = 0 if target_cell is None else int(target_cell[2]) - int(z)
    allow_parkour = True
    if target_cell is not None:
        target_vertical_delta = abs(int(target_cell[1]) - int(y))
        target_horizontal_distance = float(_horizontal_transition_distance(tuple(int(value) for value in support_cell), tuple(int(value) for value in target_cell)))
        allow_parkour = bool(int(target_vertical_delta) <= 1 and float(target_horizontal_distance) <= float(_parkour_jump_reach_blocks(ctx)) + 0.35)
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        direction_has_short_transition = False
        for dy in (0, 1, -1):
            candidate = (int(x) + int(dx), int(y) + int(dy), int(z) + int(dz))
            if candidate in avoid_cells:
                continue
            if (tuple(int(value) for value in support_cell), tuple(int(value) for value in candidate)) in blocked_edges:
                continue
            if bool(_standable_support_cell(ctx, candidate)) and bool(_transition_clear_between_support_cells(ctx, from_cell=tuple(int(value) for value in support_cell), to_cell=candidate)):
                if candidate in seen_targets:
                    break
                travel_cost = float(math.hypot(float(dx), float(dz))) + (0.25 if int(dy) > 0 else 0.0)
                candidates.append(_SupportTransition(target_cell=candidate, placement_anchor=None, jump_required=bool(int(dy) > 0), jump_span=1, travel_cost=float(travel_cost)))
                seen_targets.add(candidate)
                direction_has_short_transition = True
                break
        horizontal_candidate = (int(x) + int(dx), int(y), int(z) + int(dz))
        if int(abs(int(dx)) + abs(int(dz))) != 1:
            continue
        if horizontal_candidate in seen_targets:
            continue
        if horizontal_candidate in avoid_cells:
            continue
        if (tuple(int(value) for value in support_cell), tuple(int(value) for value in horizontal_candidate)) in blocked_edges:
            continue
        if bool(_can_place_support_block(ctx, anchor_cell=tuple(int(value) for value in support_cell), target_cell=horizontal_candidate)):
            candidates.append(_SupportTransition(target_cell=horizontal_candidate, placement_anchor=tuple(int(value) for value in support_cell), jump_required=False, jump_span=1, travel_cost=2.10))
            seen_targets.add(horizontal_candidate)
            direction_has_short_transition = True
        if bool(direction_has_short_transition):
            continue
        drop_transition = _drop_transition(ctx, support_cell=tuple(int(value) for value in support_cell), delta_x=int(dx), delta_z=int(dz))
        if drop_transition is not None:
            drop_target = tuple(int(value) for value in drop_transition.target_cell)
            if drop_target not in seen_targets and drop_target not in avoid_cells and (tuple(int(value) for value in support_cell), drop_target) not in blocked_edges:
                candidates.append(drop_transition)
                seen_targets.add(drop_target)
    if not bool(allow_parkour):
        return tuple(candidates)
    max_jump_span = int(_max_parkour_jump_span(ctx))
    for delta_x in range(-int(max_jump_span), int(max_jump_span) + 1):
        for delta_z in range(-int(max_jump_span), int(max_jump_span) + 1):
            horizontal_span = max(abs(int(delta_x)), abs(int(delta_z)))
            if int(horizontal_span) <= 1:
                continue
            if target_cell is not None and (int(delta_x) * int(target_vec_x) + int(delta_z) * int(target_vec_z)) <= 0:
                continue
            transition = _parkour_jump_transition(ctx, support_cell=tuple(int(value) for value in support_cell), delta_x=int(delta_x), delta_z=int(delta_z))
            if transition is None:
                continue
            transition_target = tuple(int(value) for value in transition.target_cell)
            if transition_target in seen_targets:
                continue
            if transition_target in avoid_cells:
                continue
            if (tuple(int(value) for value in support_cell), transition_target) in blocked_edges:
                continue
            candidates.append(transition)
            seen_targets.add(transition_target)
    return tuple(candidates)


def _support_path_heuristic(cell: tuple[int, int, int], target: tuple[int, int, int]) -> float:
    dx = float(cell[0]) - float(target[0])
    dy = float(cell[1]) - float(target[1])
    dz = float(cell[2]) - float(target[2])
    return float(math.hypot(dx, dz) + abs(dy) * 0.75)


def _plan_support_path(ctx: _PlannerContext, *, start_cell: tuple[int, int, int], target_cell: tuple[int, int, int], search_radius: int) -> tuple[AiRoutePlanStep, ...]:
    start = tuple(int(value) for value in start_cell)
    target = tuple(int(value) for value in target_cell)
    if start == target:
        return (AiRoutePlanStep(support_cell=start),)
    min_x = min(int(start[0]), int(target[0])) - int(search_radius)
    max_x = max(int(start[0]), int(target[0])) + int(search_radius)
    min_z = min(int(start[2]), int(target[2])) - int(search_radius)
    max_z = max(int(start[2]), int(target[2])) + int(search_radius)
    parent: dict[tuple[int, int, int], tuple[int, int, int] | None] = {start: None}
    placement_anchor: dict[tuple[int, int, int], tuple[int, int, int] | None] = {}
    jump_required: dict[tuple[int, int, int], bool] = {}
    jump_span: dict[tuple[int, int, int], int] = {}
    cost: dict[tuple[int, int, int], float] = {start: 0.0}
    frontier: list[tuple[float, float, tuple[int, int, int]]] = [(float(_support_path_heuristic(start, target)), 0.0, start)]
    visit_limit = max(int(_PLAN_VISIT_LIMIT_MIN), min(int(_PLAN_VISIT_LIMIT_MAX), int((2 * int(search_radius) + 1) ** 2 * 2)))
    visited = 0
    reached = False
    while frontier and int(visited) < int(visit_limit):
        _priority, current_cost, cell = heapq.heappop(frontier)
        if float(current_cost) != float(cost.get(cell, 0.0)):
            continue
        visited += 1
        if cell == target:
            reached = True
            break
        for transition in _neighbor_support_transitions(ctx, cell, target_cell=target):
            neighbor = tuple(int(value) for value in transition.target_cell)
            if int(neighbor[0]) < int(min_x) or int(neighbor[0]) > int(max_x) or int(neighbor[2]) < int(min_z) or int(neighbor[2]) > int(max_z):
                continue
            next_cost = float(current_cost) + float(transition.travel_cost)
            previous_cost = cost.get(neighbor)
            if previous_cost is not None and float(next_cost) >= float(previous_cost) - 1e-6:
                continue
            parent[neighbor] = cell
            placement_anchor[neighbor] = None if transition.placement_anchor is None else tuple(int(value) for value in transition.placement_anchor)
            jump_required[neighbor] = bool(transition.jump_required)
            jump_span[neighbor] = max(1, int(transition.jump_span))
            cost[neighbor] = float(next_cost)
            priority = float(next_cost) + float(_support_path_heuristic(neighbor, target))
            heapq.heappush(frontier, (priority, float(next_cost), neighbor))
    if not bool(reached):
        return ()
    path: list[tuple[int, int, int]] = []
    cursor: tuple[int, int, int] | None = target
    while cursor is not None:
        path.append(cursor)
        cursor = parent.get(cursor)
    path.reverse()
    steps: list[AiRoutePlanStep] = []
    for cell in path:
        normalized = tuple(int(value) for value in cell)
        steps.append(AiRoutePlanStep(support_cell=normalized, placement_anchor=None if placement_anchor.get(normalized) is None else tuple(int(value) for value in placement_anchor[normalized]), jump_required=bool(jump_required.get(normalized, False)), jump_span=max(1, int(jump_span.get(normalized, 1)))))
    return tuple(steps)


def _direct_route_clear(ctx: _PlannerContext, *, from_cell: tuple[int, int, int], to_cell: tuple[int, int, int]) -> bool:
    src = tuple(int(value) for value in from_cell)
    dst = tuple(int(value) for value in to_cell)
    if int(src[1]) != int(dst[1]):
        return False
    steps = max(abs(int(dst[0]) - int(src[0])), abs(int(dst[2]) - int(src[2])))
    if int(steps) <= 0:
        return True
    previous = src
    for index in range(1, int(steps) + 1):
        ratio = float(index) / float(steps)
        cell = (int(round(float(src[0]) + float(int(dst[0]) - int(src[0])) * ratio)), int(src[1]), int(round(float(src[2]) + float(int(dst[2]) - int(src[2])) * ratio)))
        if cell == previous:
            continue
        if not bool(_standable_support_cell(ctx, cell)):
            return False
        if not bool(_transition_clear_between_support_cells(ctx, from_cell=previous, to_cell=cell)):
            return False
        previous = cell
    return True


def compute_ai_route_plan(request: AiRoutePlanRequest) -> AiRoutePlanResult:
    world_blocks = {(int(x), int(y), int(z)): str(state_str) for x, y, z, state_str in request.world_blocks}
    world = WorldState(blocks=world_blocks, revision=int(request.world_revision))
    player = PlayerEntity(position=_support_cell_center(tuple(int(value) for value in request.start_support)), velocity=Vec3(0.0, 0.0, 0.0), yaw_deg=0.0, pitch_deg=0.0, on_ground=True)
    ctx = _PlannerContext(world=world, settings=request.settings, player=player, can_place_blocks=bool(request.can_place_blocks), blocked_edges=frozenset((tuple(int(value) for value in edge[0]), tuple(int(value) for value in edge[1])) for edge in request.blocked_edges), avoid_support_cells=frozenset(tuple(int(value) for value in cell) for cell in request.avoid_support_cells))
    start_support = tuple(int(value) for value in request.start_support)
    route_points = tuple(request.route_points)
    point_count = len(route_points)
    if point_count <= 0:
        return AiRoutePlanResult(generation=int(request.generation), actor_id=str(request.actor_id), world_revision=int(request.world_revision), start_support=start_support, route_target_index=0, success=False, path=())
    current_index = int(request.route_target_index) % int(point_count)
    route_point = route_points[int(current_index)].as_vec3()
    target_support = _nearest_standable_support_cell(ctx, _support_cell_from_point(route_point))
    if target_support is None:
        return AiRoutePlanResult(generation=int(request.generation), actor_id=str(request.actor_id), world_revision=int(request.world_revision), start_support=start_support, route_target_index=int(current_index), success=False, path=())
    if bool(_direct_route_clear(ctx, from_cell=start_support, to_cell=target_support)):
        return AiRoutePlanResult(generation=int(request.generation), actor_id=str(request.actor_id), world_revision=int(request.world_revision), start_support=start_support, route_target_index=int(current_index), success=True, path=(AiRoutePlanStep(support_cell=start_support), AiRoutePlanStep(support_cell=tuple(int(value) for value in target_support))))
    path = _plan_support_path(ctx, start_cell=start_support, target_cell=target_support, search_radius=int(request.search_radius))
    if len(path) >= 2 and tuple(int(value) for value in path[-1].support_cell) == tuple(int(value) for value in target_support):
        return AiRoutePlanResult(generation=int(request.generation), actor_id=str(request.actor_id), world_revision=int(request.world_revision), start_support=start_support, route_target_index=int(current_index), success=True, path=tuple(path))
    return AiRoutePlanResult(generation=int(request.generation), actor_id=str(request.actor_id), world_revision=int(request.world_revision), start_support=start_support, route_target_index=int(current_index), success=False, path=())
