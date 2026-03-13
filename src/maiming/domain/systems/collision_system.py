# FILE: src/maiming/domain/systems/collision_system.py
from __future__ import annotations
from dataclasses import dataclass

from ...core.math.vec3 import Vec3
from ...core.geometry.aabb import AABB
from ..entities.player_entity import PlayerEntity
from ..world.world_state import WorldState
from ..config.collision_params import CollisionParams, DEFAULT_COLLISION_PARAMS

from ..blocks.block_registry import BlockRegistry
from ..blocks.models.api import collision_aabbs_for_block
from ..blocks.state_view import def_from_state, world_state_at

@dataclass(frozen=True)
class CollisionReport:
    supported_before: bool
    supported_after: bool
    landed_now: bool
    stepped_up: bool
    step_up_dy: float
    y_correction_dy: float

@dataclass(frozen=True)
class _HorizontalMoveResult:
    pos: Vec3
    hit_ground: bool
    stepped_up: bool
    step_up_dy: float

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

def _iter_block_aabbs(world: WorldState, bx: int, by: int, bz: int, *, block_registry: BlockRegistry):
    st = world_state_at(world, int(bx), int(by), int(bz))
    if st is None:
        return

    defn = def_from_state(st, block_registry)
    if defn is not None and (not bool(defn.is_solid)):
        return

    for ba in collision_aabbs_for_block(st, lambda x, y, z: world_state_at(world, x, y, z), block_registry.get, int(bx), int(by), int(bz)):
        yield ba

def _any_intersection(world: WorldState, probe: AABB, params: CollisionParams, *, block_registry: BlockRegistry) -> bool:
    for bx, by, bz in _iter_nearby_blocks(world, probe, params):
        for ba in _iter_block_aabbs(world, bx, by, bz, block_registry=block_registry):
            if probe.intersects(ba):
                return True
    return False

def _has_support_at(player: PlayerEntity, world: WorldState, pos: Vec3, params: CollisionParams, *, block_registry: BlockRegistry) -> bool:
    eps = float(params.eps)
    gp = float(params.ground_probe)

    aabb = player.aabb_at(pos)
    probe = AABB(mn=Vec3(aabb.mn.x, aabb.mn.y - gp, aabb.mn.z), mx=Vec3(aabb.mx.x, aabb.mn.y + eps, aabb.mx.z))
    return _any_intersection(world, probe, params, block_registry=block_registry)

def _ground_probe(player: PlayerEntity, world: WorldState, params: CollisionParams, *, block_registry: BlockRegistry) -> bool:
    return _has_support_at(player, world, player.position, params, block_registry=block_registry)

def _backoff(delta: float, step: float) -> float:
    if abs(delta) <= step:
        return 0.0
    s = 1.0 if delta > 0.0 else -1.0
    v = delta - s * step
    if s > 0.0:
        return max(0.0, v)
    return min(0.0, v)

def _resolve_downward_snap(player: PlayerEntity, world: WorldState, pos: Vec3, drop: float, params: CollisionParams, *, block_registry: BlockRegistry) -> tuple[Vec3, bool]:
    eps = float(params.eps)
    dy = -float(max(0.0, drop))
    if dy >= 0.0:
        return pos, False

    pos_y = Vec3(pos.x, pos.y + dy, pos.z)
    aabb = player.aabb_at(pos_y)

    hit_ground = False
    for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
        for ba in _iter_block_aabbs(world, bx, by, bz, block_registry=block_registry):
            if aabb.intersects(ba):
                pos_y = Vec3(pos_y.x, ba.mx.y + eps, pos_y.z)
                aabb = player.aabb_at(pos_y)
                hit_ground = True

    return pos_y, bool(hit_ground)

def _has_support_within_drop(player: PlayerEntity, world: WorldState, pos: Vec3, max_drop: float, params: CollisionParams, *, block_registry: BlockRegistry) -> bool:
    _p, hit = _resolve_downward_snap(player, world, pos, float(max_drop), params, block_registry=block_registry)
    return bool(hit)

def _has_sneak_support(player: PlayerEntity, world: WorldState, pos: Vec3, params: CollisionParams, *, block_registry: BlockRegistry) -> bool:
    if _has_support_at(player, world, pos, params, block_registry=block_registry):
        return True
    return _has_support_within_drop(player, world, pos, float(params.step_height), params, block_registry=block_registry)

def _apply_sneak_edge_clamp(player: PlayerEntity, world: WorldState, pos: Vec3, delta: Vec3, params: CollisionParams, *, block_registry: BlockRegistry) -> Vec3:
    step = float(params.sneak_step)
    dx = float(delta.x)
    dz = float(delta.z)

    for _ in range(128):
        if dx == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z)
        if _has_sneak_support(player, world, cand, params, block_registry=block_registry):
            break
        dx = _backoff(dx, step)

    for _ in range(128):
        if dz == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z + dz)
        if _has_sneak_support(player, world, cand, params, block_registry=block_registry):
            break
        dz = _backoff(dz, step)

    for _ in range(256):
        if dx == 0.0 or dz == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z + dz)
        if _has_sneak_support(player, world, cand, params, block_registry=block_registry):
            break

        if abs(dx) >= abs(dz):
            dx = _backoff(dx, step)
        else:
            dz = _backoff(dz, step)

    return Vec3(dx, delta.y, dz)

def _try_step_up_height(player: PlayerEntity, world: WorldState, pos: Vec3, dx: float, dz: float, height: float, params: CollisionParams, *, block_registry: BlockRegistry) -> Vec3 | None:
    sh = float(max(0.0, height))
    if sh <= 1e-6:
        return None

    up = Vec3(pos.x, pos.y + sh, pos.z)
    if _any_intersection(world, player.aabb_at(up), params, block_registry=block_registry):
        return None

    moved = Vec3(up.x + float(dx), up.y, up.z + float(dz))
    if _any_intersection(world, player.aabb_at(moved), params, block_registry=block_registry):
        return None

    landed, hit_ground = _resolve_downward_snap(player, world, moved, sh, params, block_registry=block_registry)
    if not bool(hit_ground):
        return None

    return landed

def _axis_collision_position(player: PlayerEntity, world: WorldState, pos_try: Vec3, *, axis: str, delta: float, params: CollisionParams, block_registry: BlockRegistry) -> Vec3:
    eps = float(params.eps)
    pos_axis = pos_try
    aabb = player.aabb_at(pos_axis)

    for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
        for ba in _iter_block_aabbs(world, bx, by, bz, block_registry=block_registry):
            if not aabb.intersects(ba):
                continue

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

def _resolve_horizontal_axis_move(player: PlayerEntity, world: WorldState, pos: Vec3, *, axis: str, delta: float, allow_step: bool, params: CollisionParams, block_registry: BlockRegistry) -> _HorizontalMoveResult:
    if str(axis) == "x":
        pos_try = Vec3(pos.x + float(delta), pos.y, pos.z)
        step_dx = float(delta)
        step_dz = 0.0
    else:
        pos_try = Vec3(pos.x, pos.y, pos.z + float(delta))
        step_dx = 0.0
        step_dz = float(delta)

    if allow_step and _any_intersection(world, player.aabb_at(pos_try), params, block_registry=block_registry):
        stepped = _try_step_up_height(player, world, pos, float(step_dx), float(step_dz), float(params.step_height), params, block_registry=block_registry)
        if stepped is not None:
            return _HorizontalMoveResult(pos=stepped, hit_ground=True, stepped_up=True, step_up_dy=float(stepped.y - pos.y))

    pos_axis = _axis_collision_position(player, world, pos_try, axis=str(axis), delta=float(delta), params=params, block_registry=block_registry)
    return _HorizontalMoveResult(pos=pos_axis, hit_ground=False, stepped_up=False, step_up_dy=0.0)

def can_auto_jump_one_block(player: PlayerEntity, world: WorldState, dx: float, dz: float, *, block_registry: BlockRegistry, params: CollisionParams = DEFAULT_COLLISION_PARAMS) -> bool:
    pos = player.position
    if abs(float(dx)) + abs(float(dz)) <= 1e-9:
        return False

    if _try_step_up_height(player, world, pos, float(dx), float(dz), float(params.step_height), params, block_registry=block_registry) is not None:
        return False

    if _try_step_up_height(player, world, pos, float(dx), float(dz), 1.0, params, block_registry=block_registry) is None:
        return False

    return True

def integrate_with_collisions(player: PlayerEntity, world: WorldState, dt: float, *, block_registry: BlockRegistry, params: CollisionParams = DEFAULT_COLLISION_PARAMS, crouch: bool = False, jump_pressed: bool = False, flying: bool = False) -> CollisionReport:
    is_flying = bool(flying)
    supported_before = False if bool(is_flying) else (bool(player.on_ground) or _ground_probe(player, world, params, block_registry=block_registry))

    delta = player.velocity * float(dt)
    pos0 = player.position
    pos = pos0

    if supported_before and bool(crouch) and (not bool(jump_pressed)) and (not bool(is_flying)):
        delta = _apply_sneak_edge_clamp(player, world, pos, delta, params, block_registry=block_registry)

    intended_y = float(pos0.y) + float(delta.y)

    allow_step = (not bool(is_flying)) and bool(supported_before) and (not bool(jump_pressed)) and float(delta.y) <= 1e-9

    hit_ground = False
    stepped_up = False
    step_up_dy = 0.0

    if abs(delta.x) > 0.0:
        x_result = _resolve_horizontal_axis_move(player, world, pos, axis="x", delta=float(delta.x), allow_step=bool(allow_step), params=params, block_registry=block_registry)
        pos = x_result.pos
        hit_ground = bool(hit_ground or x_result.hit_ground)
        if bool(x_result.stepped_up):
            stepped_up = True
            step_up_dy = float(x_result.step_up_dy)

    if abs(delta.y) > 0.0:
        eps = float(params.eps)
        pos_y = Vec3(pos.x, pos.y + delta.y, pos.z)
        aabb = player.aabb_at(pos_y)
        for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
            for ba in _iter_block_aabbs(world, bx, by, bz, block_registry=block_registry):
                if aabb.intersects(ba):
                    if delta.y > 0.0:
                        pos_y = Vec3(pos_y.x, ba.mn.y - player.height - eps, pos_y.z)
                        player.velocity = Vec3(player.velocity.x, 0.0, player.velocity.z)
                    else:
                        pos_y = Vec3(pos_y.x, ba.mx.y + eps, pos_y.z)
                        player.velocity = Vec3(player.velocity.x, 0.0, player.velocity.z)
                        hit_ground = True
                    aabb = player.aabb_at(pos_y)
        pos = pos_y

    if abs(delta.z) > 0.0:
        z_result = _resolve_horizontal_axis_move(player, world, pos, axis="z", delta=float(delta.z), allow_step=bool(allow_step), params=params, block_registry=block_registry)
        pos = z_result.pos
        hit_ground = bool(hit_ground or z_result.hit_ground)
        if bool(z_result.stepped_up):
            stepped_up = True
            step_up_dy = float(z_result.step_up_dy)

    if (not bool(is_flying)) and bool(supported_before) and (not bool(jump_pressed)) and (not bool(hit_ground)) and float(player.velocity.y) <= 1e-9:
        snapped, snap_hit = _resolve_downward_snap(player, world, pos, float(params.step_height), params, block_registry=block_registry)
        if bool(snap_hit):
            pos = snapped
            hit_ground = True

    player.position = pos
    supported_after = bool(hit_ground) if bool(is_flying) else (bool(hit_ground) or _ground_probe(player, world, params, block_registry=block_registry))
    player.on_ground = supported_after

    landed_now = (not bool(is_flying)) and (not bool(supported_before)) and bool(supported_after)

    y_correction = float(pos.y) - float(intended_y)

    return CollisionReport(supported_before=bool(supported_before), supported_after=bool(supported_after), landed_now=bool(landed_now), stepped_up=bool(stepped_up), step_up_dy=float(step_up_dy), y_correction_dy=float(y_correction))