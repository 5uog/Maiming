# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ..math.vec3 import Vec3
from ..math.voxel.voxel_dda import dda_grid_traverse
from ..math.voxel.voxel_faces import face_neighbor_offset, FACE_POS_Y
from ..math.geometry.ray import Ray
from ..math.geometry.ray_aabb import ray_aabb_face

from ..world.world_state import WorldState
from ..blocks.registry.block_registry import BlockRegistry
from ..blocks.state.state_codec import parse_state
from ..blocks.state.state_view import registry_def_lookup, world_state_getter
from ..blocks.models.api import pick_aabbs_for_block
from ..blocks.structure.structural_rules import is_fence, is_wall

@dataclass(frozen=True)
class BlockPick:
    hit: tuple[int, int, int]
    place: tuple[int, int, int] | None
    t: float
    face: int
    hit_point: Vec3

def pick_block(world: WorldState, origin: Vec3, direction: Vec3, reach: float, *, block_registry: BlockRegistry) -> BlockPick | None:
    d = direction.normalized()
    if d.length() <= 1e-12:
        return None

    r = float(max(0.0, reach))
    if r <= 0.0:
        return None

    eps = 1e-4
    o = origin + d * eps
    ray = Ray(origin=o, direction=d)

    get_state = world_state_getter(world)
    get_def = registry_def_lookup(block_registry)

    prev_cell: tuple[int, int, int] | None = None

    for h in dda_grid_traverse(origin=o, direction=d, t_max=r, cell_size=1.0):
        cx, cy, cz = int(h.cell_x), int(h.cell_y), int(h.cell_z)
        k = (cx, cy, cz)

        st = world.blocks.get(k)
        if st is None:
            prev_cell = k
            continue

        aabbs = pick_aabbs_for_block(str(st), get_state, get_def, x=int(cx), y=int(cy), z=int(cz))
        if not aabbs:
            prev_cell = k
            continue

        best_t: float | None = None
        best_face: int = -1
        best_point: Vec3 | None = None

        for aabb in aabbs:
            hit = ray_aabb_face(ray, aabb)
            if hit is None:
                continue
            t = float(hit.t_enter)
            if t < -1e-9 or t > r:
                continue

            if best_t is None or t < best_t:
                best_t = t
                best_face = int(hit.face)
                best_point = hit.point

        if best_t is None or best_point is None:
            prev_cell = k
            continue

        face = int(best_face)
        if face < 0:
            face = int(h.enter_face)

        base_id, _props = parse_state(str(st))
        defn = get_def(str(base_id))

        if is_fence(defn) or is_wall(defn):
            local_y = float(best_point.y) - float(cy)
            if float(d.y) < -1e-6 and local_y >= (1.0 - 1e-6):
                face = int(FACE_POS_Y)

        ox, oy, oz = face_neighbor_offset(int(face))
        if ox == 0 and oy == 0 and oz == 0:
            place = prev_cell
        else:
            place = (int(cx + ox), int(cy + oy), int(cz + oz))

        if place is not None and place in world.blocks:
            place = None

        return BlockPick(hit=(int(cx), int(cy), int(cz)), place=place, t=float(best_t), face=int(face), hit_point=best_point)

    return None