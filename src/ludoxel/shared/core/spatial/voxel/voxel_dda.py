# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass
import math

from ...math.vec3 import Vec3

@dataclass(frozen=True)
class DDAHit:
    cell_x: int
    cell_y: int
    cell_z: int
    t: float
    enter_face: int = -1

def dda_grid_traverse(origin: Vec3, direction: Vec3, t_max: float, cell_size: float=1.0):
    d = direction
    if abs(d.x) < 1e-12 and abs(d.y) < 1e-12 and abs(d.z) < 1e-12:
        return

    x = math.floor(origin.x / cell_size)
    y = math.floor(origin.y / cell_size)
    z = math.floor(origin.z / cell_size)

    step_x = 1 if d.x > 0 else -1
    step_y = 1 if d.y > 0 else -1
    step_z = 1 if d.z > 0 else -1

    def int_bound(s: float, ds: float) -> float:
        if ds > 0:
            s = s - math.floor(s)
            return (1.0 - s) / ds
        else:
            s = s - math.floor(s)
            return s / (-ds)

    tmx = int_bound(origin.x / cell_size, d.x) if abs(d.x) > 1e-12 else 1e30
    tmy = int_bound(origin.y / cell_size, d.y) if abs(d.y) > 1e-12 else 1e30
    tmz = int_bound(origin.z / cell_size, d.z) if abs(d.z) > 1e-12 else 1e30

    tdx = (cell_size / abs(d.x)) if abs(d.x) > 1e-12 else 1e30
    tdy = (cell_size / abs(d.y)) if abs(d.y) > 1e-12 else 1e30
    tdz = (cell_size / abs(d.z)) if abs(d.z) > 1e-12 else 1e30

    t = 0.0
    enter_face = -1

    while t <= t_max:
        yield DDAHit(int(x), int(y), int(z), float(t), int(enter_face))

        if tmx < tmy and tmx < tmz:
            x += step_x
            t = tmx
            tmx += tdx
            enter_face = 1 if step_x > 0 else 0
        elif tmy < tmz:
            y += step_y
            t = tmy
            tmy += tdy
            enter_face = 3 if step_y > 0 else 2
        else:
            z += step_z
            t = tmz
            tmz += tdz
            enter_face = 5 if step_z > 0 else 4