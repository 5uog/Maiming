# FILE: src/maiming/domain/systems/build_system.py
from __future__ import annotations

from dataclasses import dataclass

from maiming.core.math.vec3 import Vec3
from maiming.core.grid.voxel_dda import dda_grid_traverse
from maiming.core.geometry.aabb import AABB
from maiming.core.geometry.ray import Ray
from maiming.core.geometry.intersection import ray_aabb_face

from maiming.domain.world.world_state import WorldState

from maiming.domain.blocks.default_registry import create_default_registry
from maiming.domain.blocks.state_codec import parse_state
from maiming.domain.blocks.models.api import pick_boxes_for_block
from maiming.domain.blocks.block_definition import FACE_POS_Y

_REG = create_default_registry()

@dataclass(frozen=True)
class BlockPick:
    hit: tuple[int, int, int]
    place: tuple[int, int, int] | None
    t: float
    face: int
    hit_point: Vec3

def _face_offset(face: int) -> tuple[int, int, int]:
    fi = int(face)
    if fi == 0:
        return (1, 0, 0)
    if fi == 1:
        return (-1, 0, 0)
    if fi == 2:
        return (0, 1, 0)
    if fi == 3:
        return (0, -1, 0)
    if fi == 4:
        return (0, 0, 1)
    if fi == 5:
        return (0, 0, -1)
    return (0, 0, 0)

def pick_block(world: WorldState, origin: Vec3, direction: Vec3, reach: float) -> BlockPick | None:
    d = direction.normalized()
    if d.length() <= 1e-12:
        return None

    r = float(max(0.0, reach))
    if r <= 0.0:
        return None

    eps = 1e-4
    o = origin + d * eps
    ray = Ray(origin=o, direction=d)

    def get_state(x: int, y: int, z: int) -> str | None:
        return world.blocks.get((int(x), int(y), int(z)))

    def get_def(base_id: str):
        return _REG.get(str(base_id))

    prev_cell: tuple[int, int, int] | None = None

    for h in dda_grid_traverse(origin=o, direction=d, t_max=r, cell_size=1.0):
        cx, cy, cz = int(h.cell_x), int(h.cell_y), int(h.cell_z)
        k = (cx, cy, cz)

        st = world.blocks.get(k)
        if st is None:
            prev_cell = k
            continue

        boxes = pick_boxes_for_block(
            str(st),
            get_state,
            get_def,
            x=cx,
            y=cy,
            z=cz,
        )
        if not boxes:
            prev_cell = k
            continue

        best_t: float | None = None
        best_face: int = -1
        best_point: Vec3 | None = None

        for b in boxes:
            aabb = AABB(
                mn=Vec3(float(cx) + float(b.mn_x), float(cy) + float(b.mn_y), float(cz) + float(b.mn_z)),
                mx=Vec3(float(cx) + float(b.mx_x), float(cy) + float(b.mx_y), float(cz) + float(b.mx_z)),
            )
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
        kind = str(defn.kind) if defn is not None else "cube"

        if kind in ("fence", "wall"):
            local_y = float(best_point.y) - float(cy)
            if float(d.y) < -1e-6 and local_y >= (1.0 - 1e-6):
                face = int(FACE_POS_Y)

        place: tuple[int, int, int] | None
        ox, oy, oz = _face_offset(face)

        if ox == 0 and oy == 0 and oz == 0:
            place = prev_cell
        else:
            place = (int(cx + ox), int(cy + oy), int(cz + oz))

        if place is not None and place in world.blocks:
            place = None

        return BlockPick(
            hit=(int(cx), int(cy), int(cz)),
            place=place,
            t=float(best_t),
            face=int(face),
            hit_point=best_point,
        )

    return None