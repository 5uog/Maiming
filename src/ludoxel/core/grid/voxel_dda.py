# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/grid/voxel_dda.py
from __future__ import annotations

from dataclasses import dataclass

import math

from ..math.vec3 import Vec3


@dataclass(frozen=True)
class DDAHit:
    """
    DDAHit = (cell_x, cell_y, cell_z, t, enter_face).

    I use this immutable record as the per-cell emission type of `dda_grid_traverse()`. The
    `cell_*` fields identify the integer voxel currently visited by the traversal, `t` stores the
    traversal parameter at which that voxel becomes current in the algorithmic state, and
    `enter_face` stores the face index through which the traversal entered that voxel. I use `-1` as
    the distinguished value for the initial voxel because the traversal starts inside that cell
    rather than crossing into it from a prior cell.

    I consume this record in `build_system.py` while marching a selection ray through voxel space.
    """
    cell_x: int
    cell_y: int
    cell_z: int
    t: float
    enter_face: int = -1


def dda_grid_traverse(origin: Vec3, direction: Vec3, t_max: float, cell_size: float=1.0):
    """
    cell_0 = (
        floor(origin.x / cell_size),
        floor(origin.y / cell_size),
        floor(origin.z / cell_size)
    )

    step_i = 1,  if d_i > 0,
            -1,  otherwise

    tMax_i =
        int_bound(origin_i / cell_size, d_i),  if abs(d_i) > 1e-12,
        1e30,                                  otherwise

    tDelta_i =
        cell_size / abs(d_i),  if abs(d_i) > 1e-12,
        1e30,                  otherwise.

    I implement a voxel-grid traversal in the Amanatides-Woo style. I start from the cell containing
    `origin`, advance the ray in increasing parametric order, and yield one `DDAHit` for each visited
    cell while the running parameter `t` satisfies `t <= t_max`.

    The zero-direction guard is exact and immediate. If all three direction components satisfy
    `abs(d_i) < 1e-12`, I terminate the generator without yielding anything. Otherwise I compute the
    starting voxel indices by `floor(origin_i / cell_size)`, derive per-axis step signs by the
    branch `1 if d_i > 0 else -1`, and initialize per-axis next-boundary parameters and per-cell
    increments.

    The internal helper `int_bound(s, ds)` has the exact law

        int_bound(s, ds) =
            (1 - frac(s)) / ds,  if ds > 0,
            frac(s) / (-ds),     otherwise,

    where `frac(s) = s - floor(s)`. Because I call it only when `abs(ds) > 1e-12`, its `else`
    branch handles the negative-direction case, not a true zero denominator case. In particular, if
    the starting coordinate lies exactly on an integer grid boundary and the ray points in the
    negative direction, the returned value is `0.0`, so the traversal crosses into the adjacent
    negative cell immediately after yielding the initial cell.

    The tie policy is also literal. I choose the next axis by

        x,  if tmx < tmy and tmx < tmz,
        y,  elif tmy < tmz,
        z,  otherwise.

    Consequently, equal ties are not broken symmetrically. X loses every tie against Y or Z, Y loses
    every remaining tie against Z, and Z wins the residual equal-case branch. The `enter_face`
    written into the next yielded voxel is the face opposite the stepping direction:
    moving by `+X` stores `FACE_NEG_X`, moving by `-X` stores `FACE_POS_X`, and analogously for Y
    and Z through the raw integer constants `1/0`, `3/2`, and `5/4` used in the implementation.

    I do not validate `cell_size`. Ordinary behavior therefore presupposes that the caller supplies a
    non-zero cell size. In my own code I invoke this traversal from `build_system.py` with the
    default `cell_size = 1.0` while marching block-selection rays.
    """
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
