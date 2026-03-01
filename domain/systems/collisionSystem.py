# FILE: domain/systems/collisionSystem.py
from __future__ import annotations

from dataclasses import dataclass

from core.math.vec3 import Vec3
from core.geometry.aabb import AABB
from domain.entities.playerEntity import PlayerEntity
from domain.world.worldState import WorldState
from domain.config.collisionParams import CollisionParams, DEFAULT_COLLISION_PARAMS

from domain.blocks.blockRegistry import create_default_registry
from domain.blocks.stateCodec import parse_state
from domain.blocks.runtimeModels import collision_boxes_for_block

_REG = create_default_registry()

@dataclass(frozen=True)
class CollisionReport:
    supported_before: bool
    supported_after: bool
    landed_now: bool
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

def _world_get_state(world: WorldState, x: int, y: int, z: int) -> str | None:
    return world.blocks.get((int(x), int(y), int(z)))

def _get_def(base_id: str):
    return _REG.get(str(base_id))

def _iter_block_aabbs(world: WorldState, bx: int, by: int, bz: int):
    st = world.blocks.get((int(bx), int(by), int(bz)))
    if st is None:
        return
    base, _p = parse_state(st)
    defn = _REG.get(str(base))
    if defn is not None and (not bool(defn.is_solid)):
        return

    boxes = collision_boxes_for_block(st, lambda x, y, z: _world_get_state(world, x, y, z), _get_def, bx, by, bz)
    for b in boxes:
        yield AABB(
            mn=Vec3(float(bx) + float(b.mn_x), float(by) + float(b.mn_y), float(bz) + float(b.mn_z)),
            mx=Vec3(float(bx) + float(b.mx_x), float(by) + float(b.mx_y), float(bz) + float(b.mx_z)),
        )

def _any_intersection(world: WorldState, probe: AABB, params: CollisionParams) -> bool:
    for bx, by, bz in _iter_nearby_blocks(world, probe, params):
        for ba in _iter_block_aabbs(world, bx, by, bz):
            if probe.intersects(ba):
                return True
    return False

def _has_support_at(player: PlayerEntity, world: WorldState, pos: Vec3, params: CollisionParams) -> bool:
    eps = float(params.eps)
    gp = float(params.ground_probe)

    aabb = player.aabb_at(pos)
    probe = AABB(
        mn=Vec3(aabb.mn.x, aabb.mn.y - gp, aabb.mn.z),
        mx=Vec3(aabb.mx.x, aabb.mn.y + eps, aabb.mx.z),
    )
    return _any_intersection(world, probe, params)

def _ground_probe(player: PlayerEntity, world: WorldState, params: CollisionParams) -> bool:
    return _has_support_at(player, world, player.position, params)

def _backoff(delta: float, step: float) -> float:
    if abs(delta) <= step:
        return 0.0
    s = 1.0 if delta > 0.0 else -1.0
    v = delta - s * step
    if s > 0.0:
        return max(0.0, v)
    return min(0.0, v)

def _apply_sneak_edge_clamp(
    player: PlayerEntity,
    world: WorldState,
    pos: Vec3,
    delta: Vec3,
    params: CollisionParams,
) -> Vec3:
    step = float(params.sneak_step)
    dx = float(delta.x)
    dz = float(delta.z)

    for _ in range(128):
        if dx == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z)
        if _has_support_at(player, world, cand, params):
            break
        dx = _backoff(dx, step)

    for _ in range(128):
        if dz == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z + dz)
        if _has_support_at(player, world, cand, params):
            break
        dz = _backoff(dz, step)

    for _ in range(256):
        if dx == 0.0 or dz == 0.0:
            break
        cand = Vec3(pos.x + dx, pos.y, pos.z + dz)
        if _has_support_at(player, world, cand, params):
            break

        if abs(dx) >= abs(dz):
            dx = _backoff(dx, step)
        else:
            dz = _backoff(dz, step)

    return Vec3(dx, delta.y, dz)

def _resolve_downward_snap(
    player: PlayerEntity,
    world: WorldState,
    pos: Vec3,
    drop: float,
    params: CollisionParams,
) -> tuple[Vec3, bool]:
    eps = float(params.eps)
    dy = -float(max(0.0, drop))
    if dy >= 0.0:
        return pos, False

    pos_y = Vec3(pos.x, pos.y + dy, pos.z)
    aabb = player.aabb_at(pos_y)

    hit_ground = False
    for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
        for ba in _iter_block_aabbs(world, bx, by, bz):
            if aabb.intersects(ba):
                pos_y = Vec3(pos_y.x, ba.mx.y + eps, pos_y.z)
                aabb = player.aabb_at(pos_y)
                hit_ground = True

    return pos_y, bool(hit_ground)

def _try_step_up_height(
    player: PlayerEntity,
    world: WorldState,
    pos: Vec3,
    dx: float,
    dz: float,
    height: float,
    params: CollisionParams,
) -> Vec3 | None:
    sh = float(max(0.0, height))
    if sh <= 1e-6:
        return None

    up = Vec3(pos.x, pos.y + sh, pos.z)
    if _any_intersection(world, player.aabb_at(up), params):
        return None

    moved = Vec3(up.x + float(dx), up.y, up.z + float(dz))
    if _any_intersection(world, player.aabb_at(moved), params):
        return None

    landed, hit_ground = _resolve_downward_snap(player, world, moved, sh, params)
    if not bool(hit_ground):
        return None

    return landed

def can_auto_jump_one_block(
    player: PlayerEntity,
    world: WorldState,
    dx: float,
    dz: float,
    params: CollisionParams = DEFAULT_COLLISION_PARAMS,
) -> bool:
    pos = player.position
    if abs(float(dx)) + abs(float(dz)) <= 1e-9:
        return False

    if _try_step_up_height(player, world, pos, float(dx), float(dz), float(params.step_height), params) is not None:
        return False

    if _try_step_up_height(player, world, pos, float(dx), float(dz), 1.0, params) is None:
        return False

    return True

def integrate_with_collisions(
    player: PlayerEntity,
    world: WorldState,
    dt: float,
    params: CollisionParams = DEFAULT_COLLISION_PARAMS,
    crouch: bool = False,
    jump_pressed: bool = False,
) -> CollisionReport:
    eps = float(params.eps)

    supported_before = bool(player.on_ground) or _ground_probe(player, world, params)

    delta = player.velocity * float(dt)
    pos = player.position

    if supported_before and bool(crouch) and (not bool(jump_pressed)):
        delta = _apply_sneak_edge_clamp(player, world, pos, delta, params)

    allow_step = bool(supported_before) and (not bool(crouch)) and (not bool(jump_pressed)) and float(delta.y) <= 1e-9

    hit_ground = False
    stepped_up = False
    step_up_dy = 0.0

    if abs(delta.x) > 0.0:
        pos_try = Vec3(pos.x + delta.x, pos.y, pos.z)
        if allow_step and _any_intersection(world, player.aabb_at(pos_try), params):
            stepped = _try_step_up_height(player, world, pos, float(delta.x), 0.0, float(params.step_height), params)
            if stepped is not None:
                step_up_dy = float(stepped.y - pos.y)
                pos = stepped
                hit_ground = True
                stepped_up = True
            else:
                pos_x = pos_try
                aabb = player.aabb_at(pos_x)
                for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
                    for ba in _iter_block_aabbs(world, bx, by, bz):
                        if aabb.intersects(ba):
                            if delta.x > 0.0:
                                pos_x = Vec3(ba.mn.x - (player.width * 0.5) - eps, pos_x.y, pos_x.z)
                            else:
                                pos_x = Vec3(ba.mx.x + (player.width * 0.5) + eps, pos_x.y, pos_x.z)
                            player.velocity = Vec3(0.0, player.velocity.y, player.velocity.z)
                            aabb = player.aabb_at(pos_x)
                pos = pos_x
        else:
            pos_x = pos_try
            aabb = player.aabb_at(pos_x)
            for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
                for ba in _iter_block_aabbs(world, bx, by, bz):
                    if aabb.intersects(ba):
                        if delta.x > 0.0:
                            pos_x = Vec3(ba.mn.x - (player.width * 0.5) - eps, pos_x.y, pos_x.z)
                        else:
                            pos_x = Vec3(ba.mx.x + (player.width * 0.5) + eps, pos_x.y, pos_x.z)
                        player.velocity = Vec3(0.0, player.velocity.y, player.velocity.z)
                        aabb = player.aabb_at(pos_x)
            pos = pos_x

    if abs(delta.y) > 0.0:
        pos_y = Vec3(pos.x, pos.y + delta.y, pos.z)
        aabb = player.aabb_at(pos_y)
        for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
            for ba in _iter_block_aabbs(world, bx, by, bz):
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
        pos_try = Vec3(pos.x, pos.y, pos.z + delta.z)
        if allow_step and _any_intersection(world, player.aabb_at(pos_try), params):
            stepped = _try_step_up_height(player, world, pos, 0.0, float(delta.z), float(params.step_height), params)
            if stepped is not None:
                step_up_dy = float(stepped.y - pos.y)
                pos = stepped
                hit_ground = True
                stepped_up = True
            else:
                pos_z = pos_try
                aabb = player.aabb_at(pos_z)
                for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
                    for ba in _iter_block_aabbs(world, bx, by, bz):
                        if aabb.intersects(ba):
                            if delta.z > 0.0:
                                pos_z = Vec3(pos_z.x, pos_z.y, ba.mn.z - (player.width * 0.5) - eps)
                            else:
                                pos_z = Vec3(pos_z.x, pos_z.y, ba.mx.z + (player.width * 0.5) + eps)
                            player.velocity = Vec3(player.velocity.x, player.velocity.y, 0.0)
                            aabb = player.aabb_at(pos_z)
                pos = pos_z
        else:
            pos_z = pos_try
            aabb = player.aabb_at(pos_z)
            for bx, by, bz in _iter_nearby_blocks(world, aabb, params):
                for ba in _iter_block_aabbs(world, bx, by, bz):
                    if aabb.intersects(ba):
                        if delta.z > 0.0:
                            pos_z = Vec3(pos_z.x, pos_z.y, ba.mn.z - (player.width * 0.5) - eps)
                        else:
                            pos_z = Vec3(pos_z.x, pos_z.y, ba.mx.z + (player.width * 0.5) + eps)
                        player.velocity = Vec3(player.velocity.x, player.velocity.y, 0.0)
                        aabb = player.aabb_at(pos_z)
            pos = pos_z

    player.position = pos
    supported_after = bool(hit_ground) or _ground_probe(player, world, params)
    player.on_ground = supported_after

    landed_now = (not bool(supported_before)) and bool(supported_after)

    return CollisionReport(
        supported_before=bool(supported_before),
        supported_after=bool(supported_after),
        landed_now=bool(landed_now),
        stepped_up=bool(stepped_up),
        step_up_dy=float(step_up_dy),
    )