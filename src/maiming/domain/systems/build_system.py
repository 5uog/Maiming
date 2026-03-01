# FILE: src/maiming/domain/systems/build_system.py
from __future__ import annotations

from dataclasses import dataclass

from maiming.core.math.vec3 import Vec3
from maiming.core.grid.voxel_dda import dda_grid_traverse

from maiming.domain.world.world_state import WorldState

@dataclass(frozen=True)
class BlockPick:
    hit: tuple[int, int, int]
    place: tuple[int, int, int] | None
    t: float
    face: int
    hit_point: Vec3

def pick_block(world: WorldState, origin: Vec3, direction: Vec3, reach: float) -> BlockPick | None:
    d = direction.normalized()
    if d.length() <= 1e-12:
        return None

    r = float(max(0.0, reach))
    if r <= 0.0:
        return None

    eps = 1e-4
    o = origin + d * eps

    prev: tuple[int, int, int] | None = None

    for h in dda_grid_traverse(origin=o, direction=d, t_max=r, cell_size=1.0):
        k = (int(h.cell_x), int(h.cell_y), int(h.cell_z))

        if k in world.blocks:
            place = prev
            if place is not None and place in world.blocks:
                place = None
            hp = o + d * float(h.t)
            return BlockPick(hit=k, place=place, t=float(h.t), face=int(h.enter_face), hit_point=hp)

        prev = k

    return None