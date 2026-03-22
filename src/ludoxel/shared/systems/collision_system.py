# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ..math.vec3 import Vec3
from ..math.geometry.aabb import AABB
from ..world.entities.player_entity import PlayerEntity
from ..world.world_state import WorldState
from ..world.config.collision_params import CollisionParams, DEFAULT_COLLISION_PARAMS

from ..blocks.registry.block_registry import BlockRegistry
from ..blocks.models.api import collision_aabbs_for_block
from ..blocks.state.state_codec import parse_state
from ..blocks.state.state_values import prop_as_bool
from ..blocks.state.state_view import def_from_state, world_state_at
from ..blocks.structure.structural_rules import is_fence_gate
from .gravity_system import GRAVITY_AFFECTED_TAG


@dataclass(frozen=True)
class CollisionReport:
    supported_before: bool
    supported_after: bool
    landed_now: bool
    stepped_up: bool
    step_up_dy: float
    y_correction_dy: float


@dataclass(frozen=True)
class SupportBlockContact:
    cell: tuple[int, int, int]
    block_state: str
    support_y: float


@dataclass(frozen=True)
class _HorizontalMoveResult:
    pos: Vec3
    hit_ground: bool
    stepped_up: bool
    step_up_dy: float


def _normalize_exempt_cells(collision_exempt_cell: object) -> frozenset[tuple[int, int, int]]:
    if collision_exempt_cell is None:
        return frozenset()
    if isinstance(collision_exempt_cell, frozenset):
        return collision_exempt_cell
    if isinstance(collision_exempt_cell, tuple) and len(collision_exempt_cell) == 3:
        return frozenset({(int(collision_exempt_cell[0]), int(collision_exempt_cell[1]), int(collision_exempt_cell[2]))})
    if isinstance(collision_exempt_cell,(set, list, tuple)):
        out: set[tuple[int, int, int]] = set()
        for cell in collision_exempt_cell:
            if isinstance(cell, tuple) and len(cell) == 3:
                out.add((int(cell[0]), int(cell[1]), int(cell[2])))
        return frozenset(out)
    return frozenset()


def _iter_nearby_blocks(world: WorldState, aabb: AABB, params: CollisionParams):
    pxz = int(params.nearby_xz_pad)
    pyd = int(params.nearby_y_down_pad)
    pyu = int(params.nearby_y_up_pad)

    x0 = int(aabb.mn.x) - pxz
    x1 = int(aabb.mx.x) + pxz
    y0 = int(aabb.mn.y) - pyd
    y1 = int(aabb.mx.y) + pyu
    z0 = int(aabb.mn.z) - pxz
    z1 = int(aabb.mx.z) + pxz

    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                if (x, y, z) in world.blocks:
                    yield x, y, z


def _active_fence_gate_overlap_exemption(player: PlayerEntity, world: WorldState, *, block_registry: BlockRegistry) -> tuple[int, int, int] | None:
    cell = player.fence_gate_overlap_exemption
    if cell is None:
        return None

    x, y, z = (int(cell[0]), int(cell[1]), int(cell[2]))
    state_str = world_state_at(world, int(x), int(y), int(z))
    defn = def_from_state(state_str, block_registry)
    if state_str is None or defn is None or (not is_fence_gate(defn)):
        player.fence_gate_overlap_exemption = None
        return None

    _base, props = parse_state(str(state_str))
    if prop_as_bool(props, "open", False):
        player.fence_gate_overlap_exemption = None
        return None

    player_aabb = player.aabb_at(player.position)
    for box in collision_aabbs_for_block(str(state_str), lambda gx, gy, gz: world_state_at(world, gx, gy, gz), block_registry.get, int(x), int(y), int(z)):
        if player_aabb.intersects(box):
            return (int(x), int(y), int(z))

    player.fence_gate_overlap_exemption = None
    return None


def _active_gravity_block_overlap_exemptions(player: PlayerEntity, world: WorldState, *, block_registry: BlockRegistry) -> frozenset[tuple[int, int, int]]:
    cells = tuple(player.gravity_block_overlap_exemptions)
    if not cells:
        return frozenset()

    player_aabb = player.aabb_at(player.position)
    active: set[tuple[int, int, int]] = set()
    for cell in cells:
        x, y, z = (int(cell[0]), int(cell[1]), int(cell[2]))
        state_str = world_state_at(world, int(x), int(y), int(z))
        defn = def_from_state(state_str, block_registry)
        if state_str is None or defn is None or (not defn.has_tag(GRAVITY_AFFECTED_TAG)):
            continue
        for box in collision_aabbs_for_block(str(state_str), lambda gx, gy, gz: world_state_at(world, gx, gy, gz), block_registry.get, int(x), int(y), int(z)):
            if player_aabb.intersects(box):
                active.add((int(x), int(y), int(z)))
                break

    player.gravity_block_overlap_exemptions = tuple(sorted(active))
    return frozenset(active)


def _active_collision_exempt_cells(player: PlayerEntity, world: WorldState, *, block_registry: BlockRegistry) -> frozenset[tuple[int, int, int]]:
    out: set[tuple[int, int, int]] = set()
    fence_gate_cell = _active_fence_gate_overlap_exemption(player, world, block_registry=block_registry)
    if fence_gate_cell is not None:
        out.add((int(fence_gate_cell[0]), int(fence_gate_cell[1]), int(fence_gate_cell[2])))
    out.update(_active_gravity_block_overlap_exemptions(player, world, block_registry=block_registry))
    return frozenset(out)


def _iter_block_aabbs(world: WorldState, bx: int, by: int, bz: int, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None):
    if (int(bx), int(by), int(bz)) in _normalize_exempt_cells(collision_exempt_cell):
        return

    st = world_state_at(world, int(bx), int(by), int(bz))
    if st is None:
        return

    defn = def_from_state(st, block_registry)
    if defn is not None and (not bool(defn.is_solid)):
        return

    for ba in collision_aabbs_for_block(str(st), lambda x, y, z: world_state_at(world, x, y, z), block_registry.get, int(bx), int(by), int(bz)):
        yield ba


def _iter_intersections(world: WorldState, probe: AABB, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None):
    for bx, by, bz in _iter_nearby_blocks(world, probe, params):
        for ba in _iter_block_aabbs(world, bx, by, bz, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
            if probe.intersects(ba):
                yield (int(bx), int(by), int(bz), ba)


def _any_intersection(world: WorldState, probe: AABB, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> bool:
    for _bx, _by, _bz, _ba in _iter_intersections(world, probe, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        return True
    return False


def _depenetrate(player: PlayerEntity, world: WorldState, pos: Vec3, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> tuple[Vec3, Vec3]:
    eps = float(params.eps)
    current = Vec3(float(pos.x), float(pos.y), float(pos.z))
    total_shift = Vec3(0.0, 0.0, 0.0)

    for _ in range(16):
        aabb = player.aabb_at(current)
        best_shift: Vec3 | None = None
        best_abs = float("inf")

        for _bx, _by, _bz, block_aabb in _iter_intersections(world, aabb, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
            shift_candidates = (Vec3(float(block_aabb.mn.x) - float(aabb.mx.x) - eps, 0.0, 0.0), Vec3(float(block_aabb.mx.x) - float(aabb.mn.x) + eps, 0.0, 0.0), Vec3(0.0, float(block_aabb.mn.y) - float(aabb.mx.y) - eps, 0.0), Vec3(0.0, float(block_aabb.mx.y) - float(aabb.mn.y) + eps, 0.0), Vec3(0.0, 0.0, float(block_aabb.mn.z) - float(aabb.mx.z) - eps), Vec3(0.0, 0.0, float(block_aabb.mx.z) - float(aabb.mn.z) + eps))
            for shift in shift_candidates:
                magnitude = abs(float(shift.x)) + abs(float(shift.y)) + abs(float(shift.z))
                if magnitude < float(best_abs):
                    best_abs = float(magnitude)
                    best_shift = shift

        if best_shift is None:
            break

        current = Vec3(float(current.x) + float(best_shift.x), float(current.y) + float(best_shift.y), float(current.z) + float(best_shift.z))
        total_shift = Vec3(float(total_shift.x) + float(best_shift.x), float(total_shift.y) + float(best_shift.y), float(total_shift.z) + float(best_shift.z))

    return (current, total_shift)


def _has_support_at(player: PlayerEntity, world: WorldState, pos: Vec3, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> bool:
    eps = float(params.eps)
    gp = float(params.ground_probe)

    aabb = player.aabb_at(pos)
    probe = AABB(mn=Vec3(aabb.mn.x, aabb.mn.y - gp, aabb.mn.z), mx=Vec3(aabb.mx.x, aabb.mn.y + eps, aabb.mx.z))
    return _any_intersection(world, probe, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)


def _ground_probe(player: PlayerEntity, world: WorldState, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> bool:
    return _has_support_at(player, world, player.position, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)


def support_block_beneath(player: PlayerEntity, world: WorldState, *, block_registry: BlockRegistry, params: CollisionParams=DEFAULT_COLLISION_PARAMS, collision_exempt_cell: tuple[int, int, int] | None=None) -> SupportBlockContact | None:
    feet_y = float(player.position.y)
    eps = float(max(float(params.eps), 1e-5))
    probe_depth = float(max(float(params.ground_probe), eps * 2.0, 0.25))
    aabb = player.aabb_at(player.position)
    probe = AABB(mn=Vec3(aabb.mn.x, feet_y - probe_depth, aabb.mn.z), mx=Vec3(aabb.mx.x, feet_y + eps, aabb.mx.z))

    best_contact: SupportBlockContact | None = None
    best_support_y = float("-inf")

    for bx, by, bz in _iter_nearby_blocks(world, probe, params):
        block_state = world_state_at(world, int(bx), int(by), int(bz))
        if block_state is None:
            continue

        defn = def_from_state(block_state, block_registry)
        if defn is not None and (not bool(defn.is_solid)):
            continue

        for block_aabb in _iter_block_aabbs(world, bx, by, bz, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
            if float(block_aabb.mx.y) < float(feet_y - probe_depth) or float(block_aabb.mx.y) > float(feet_y + eps):
                continue
            if float(aabb.mx.x) <= float(block_aabb.mn.x) + eps or float(aabb.mn.x) >= float(block_aabb.mx.x) - eps:
                continue
            if float(aabb.mx.z) <= float(block_aabb.mn.z) + eps or float(aabb.mn.z) >= float(block_aabb.mx.z) - eps:
                continue
            support_y = float(block_aabb.mx.y)
            if support_y > float(best_support_y):
                best_support_y = float(support_y)
                best_contact = SupportBlockContact(cell=(int(bx), int(by), int(bz)), block_state=str(block_state), support_y=float(support_y))

    return best_contact


def _backoff(delta: float, step: float) -> float:
    if abs(delta) <= step:
        return 0.0
    s = 1.0 if delta > 0.0 else -1.0
    v = delta - s * step
    if s > 0.0:
        return max(0.0, v)
    return min(0.0, v)


def _resolve_downward_snap(player: PlayerEntity, world: WorldState, pos: Vec3, drop: float, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> tuple[Vec3, bool]:
    eps = float(params.eps)
    dy = -float(max(0.0, drop))
    if dy >= 0.0:
        return pos, False

    pos_y = Vec3(pos.x, pos.y + dy, pos.z)
    aabb = player.aabb_at(pos_y)
    best_support_y: float | None = None
    for _bx, _by, _bz, ba in _iter_intersections(world, aabb, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        top_y = float(ba.mx.y)
        if best_support_y is None or top_y > float(best_support_y):
            best_support_y = float(top_y)

    if best_support_y is None:
        return pos, False

    return Vec3(pos_y.x, float(best_support_y) + eps, pos_y.z), True


def _has_support_within_drop(player: PlayerEntity, world: WorldState, pos: Vec3, max_drop: float, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> bool:
    _p, hit = _resolve_downward_snap(player, world, pos, float(max_drop), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
    return bool(hit)


def _has_sneak_support(player: PlayerEntity, world: WorldState, pos: Vec3, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> bool:
    if _has_support_at(player, world, pos, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        return True
    return _has_support_within_drop(player, world, pos, float(params.step_height), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)


def _apply_sneak_edge_clamp(player: PlayerEntity, world: WorldState, pos: Vec3, delta: Vec3, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> Vec3:
    step = float(params.sneak_step)
    dx = float(delta.x)
    dz = float(delta.z)

    for _ in range(128):
        if dx == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z)
        if _has_sneak_support(player, world, cand, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
            break
        dx = _backoff(dx, step)

    for _ in range(128):
        if dz == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z + dz)
        if _has_sneak_support(player, world, cand, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
            break
        dz = _backoff(dz, step)

    for _ in range(256):
        if dx == 0.0 or dz == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z + dz)
        if _has_sneak_support(player, world, cand, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
            break

        if abs(dx) >= abs(dz):
            dx = _backoff(dx, step)
        else:
            dz = _backoff(dz, step)

    return Vec3(dx, delta.y, dz)


def _try_step_up_height(player: PlayerEntity, world: WorldState, pos: Vec3, dx: float, dz: float, height: float, params: CollisionParams, *, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> Vec3 | None:
    sh = float(max(0.0, height))
    if sh <= 1e-6:
        return None

    up = Vec3(pos.x, pos.y + sh, pos.z)
    if _any_intersection(world, player.aabb_at(up), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        return None

    moved = Vec3(up.x + float(dx), up.y, up.z + float(dz))
    if _any_intersection(world, player.aabb_at(moved), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        return None

    landed, hit_ground = _resolve_downward_snap(player, world, moved, sh, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
    if not bool(hit_ground):
        return None

    return landed


def _axis_collision_position(player: PlayerEntity, world: WorldState, pos_try: Vec3, *, axis: str, delta: float, params: CollisionParams, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> Vec3:
    eps = float(params.eps)
    pos_axis = pos_try
    aabb = player.aabb_at(pos_axis)

    for _bx, _by, _bz, ba in _iter_intersections(world, aabb, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        if str(axis) == "x":
            if float(delta) > 0.0:
                pos_axis = Vec3(ba.mn.x - (player.width * 0.5) - eps, pos_axis.y, pos_axis.z)
            else:
                pos_axis = Vec3(ba.mx.x + (player.width * 0.5) + eps, pos_axis.y, pos_axis.z)
            player.velocity = Vec3(0.0, player.velocity.y, player.velocity.z)
        else:
            if float(delta) > 0.0:
                pos_axis = Vec3(pos_axis.x, pos_axis.y, ba.mn.z - (player.width * 0.5) - eps)
            else:
                pos_axis = Vec3(pos_axis.x, pos_axis.y, ba.mx.z + (player.width * 0.5) + eps)
            player.velocity = Vec3(player.velocity.x, player.velocity.y, 0.0)

        aabb = player.aabb_at(pos_axis)

    return pos_axis


def _resolve_horizontal_axis_move(player: PlayerEntity, world: WorldState, pos: Vec3, *, axis: str, delta: float, allow_step: bool, params: CollisionParams, block_registry: BlockRegistry, collision_exempt_cell: tuple[int, int, int] | None=None) -> _HorizontalMoveResult:
    if str(axis) == "x":
        pos_try = Vec3(pos.x + float(delta), pos.y, pos.z)
        step_dx = float(delta)
        step_dz = 0.0
    else:
        pos_try = Vec3(pos.x, pos.y, pos.z + float(delta))
        step_dx = 0.0
        step_dz = float(delta)

    if allow_step and _any_intersection(world, player.aabb_at(pos_try), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        stepped = _try_step_up_height(player, world, pos, float(step_dx), float(step_dz), float(params.step_height), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
        if stepped is not None:
            return _HorizontalMoveResult(pos=stepped, hit_ground=True, stepped_up=True, step_up_dy=float(stepped.y - pos.y))

    pos_axis = _axis_collision_position(player, world, pos_try, axis=str(axis), delta=float(delta), params=params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
    return _HorizontalMoveResult(pos=pos_axis, hit_ground=False, stepped_up=False, step_up_dy=0.0)


def can_auto_jump_one_block(player: PlayerEntity, world: WorldState, dx: float, dz: float, *, block_registry: BlockRegistry, params: CollisionParams=DEFAULT_COLLISION_PARAMS) -> bool:
    pos = player.position
    if abs(float(dx)) + abs(float(dz)) <= 1e-9:
        return False

    collision_exempt_cell = _active_collision_exempt_cells(player, world, block_registry=block_registry)

    if _try_step_up_height(player, world, pos, float(dx), float(dz), float(params.step_height), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell) is not None:
        return False

    if _try_step_up_height(player, world, pos, float(dx), float(dz), 1.0, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell) is None:
        return False

    return True


def integrate_with_collisions(player: PlayerEntity, world: WorldState, dt: float, *, block_registry: BlockRegistry, params: CollisionParams=DEFAULT_COLLISION_PARAMS, crouch: bool=False, jump_pressed: bool=False, flying: bool=False) -> CollisionReport:
    is_flying = bool(flying)
    collision_exempt_cell = _active_collision_exempt_cells(player, world, block_registry=block_registry)
    rising_eps = float(max(float(params.eps), 1e-6))

    if _any_intersection(world, player.aabb_at(player.position), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
        depenetrated_pos, initial_shift = _depenetrate(player, world, player.position, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
        if abs(float(initial_shift.x)) > 1e-9:
            player.velocity = Vec3(0.0, player.velocity.y, player.velocity.z)
        if abs(float(initial_shift.y)) > 1e-9:
            player.velocity = Vec3(player.velocity.x, 0.0, player.velocity.z)
        if abs(float(initial_shift.z)) > 1e-9:
            player.velocity = Vec3(player.velocity.x, player.velocity.y, 0.0)
        player.position = depenetrated_pos

    supported_before = False if bool(is_flying) else (((bool(player.on_ground) and float(player.velocity.y) <= float(rising_eps)) or ((not bool(player.on_ground)) and _ground_probe(player, world, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell))))

    delta = player.velocity * float(dt)
    pos0 = player.position
    pos = pos0

    if supported_before and bool(crouch) and (not bool(jump_pressed)) and (not bool(is_flying)):
        delta = _apply_sneak_edge_clamp(player, world, pos, delta, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)

    intended_y = float(pos0.y) + float(delta.y)

    allow_step = (not bool(is_flying)) and bool(supported_before) and (not bool(jump_pressed)) and float(delta.y) <= 1e-9

    hit_ground = False
    stepped_up = False
    step_up_dy = 0.0

    if abs(delta.x) > 0.0:
        x_result = _resolve_horizontal_axis_move(player, world, pos, axis="x", delta=float(delta.x), allow_step=bool(allow_step), params=params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
        pos = x_result.pos
        hit_ground = bool(hit_ground or x_result.hit_ground)
        if bool(x_result.stepped_up):
            stepped_up = True
            step_up_dy = float(x_result.step_up_dy)

    if abs(delta.y) > 0.0:
        eps = float(params.eps)
        pos_y = Vec3(pos.x, pos.y + delta.y, pos.z)
        aabb = player.aabb_at(pos_y)
        if delta.y > 0.0:
            lowest_ceiling_y: float | None = None
            for _bx, _by, _bz, ba in _iter_intersections(world, aabb, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
                bottom_y = float(ba.mn.y)
                if lowest_ceiling_y is None or bottom_y < float(lowest_ceiling_y):
                    lowest_ceiling_y = float(bottom_y)
            if lowest_ceiling_y is not None:
                pos_y = Vec3(pos_y.x, float(lowest_ceiling_y) - player.height - eps, pos_y.z)
                player.velocity = Vec3(player.velocity.x, 0.0, player.velocity.z)
        else:
            highest_floor_y: float | None = None
            for _bx, _by, _bz, ba in _iter_intersections(world, aabb, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell):
                top_y = float(ba.mx.y)
                if highest_floor_y is None or top_y > float(highest_floor_y):
                    highest_floor_y = float(top_y)
            if highest_floor_y is not None:
                pos_y = Vec3(pos_y.x, float(highest_floor_y) + eps, pos_y.z)
                player.velocity = Vec3(player.velocity.x, 0.0, player.velocity.z)
                hit_ground = True
        pos = pos_y

    if abs(delta.z) > 0.0:
        z_result = _resolve_horizontal_axis_move(player, world, pos, axis="z", delta=float(delta.z), allow_step=bool(allow_step), params=params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
        pos = z_result.pos
        hit_ground = bool(hit_ground or z_result.hit_ground)
        if bool(z_result.stepped_up):
            stepped_up = True
            step_up_dy = float(z_result.step_up_dy)

    if (not bool(is_flying)) and bool(supported_before) and (not bool(jump_pressed)) and (not bool(hit_ground)) and float(player.velocity.y) <= 1e-9:
        snapped, snap_hit = _resolve_downward_snap(player, world, pos, float(params.step_height), params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)
        if bool(snap_hit):
            pos = snapped
            hit_ground = True

    player.position = pos
    supported_after = bool(hit_ground) if bool(is_flying) else (bool(hit_ground) or ((float(player.velocity.y) <= float(rising_eps)) and _ground_probe(player, world, params, block_registry=block_registry, collision_exempt_cell=collision_exempt_cell)))
    player.on_ground = supported_after

    landed_now = (not bool(is_flying)) and (not bool(supported_before)) and bool(supported_after)

    y_correction = float(pos.y) - float(intended_y)

    return CollisionReport(supported_before=bool(supported_before), supported_after=bool(supported_after), landed_now=bool(landed_now), stepped_up=bool(stepped_up), step_up_dy=float(step_up_dy), y_correction_dy=float(y_correction))
