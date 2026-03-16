# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/geometry/intersection.py
from __future__ import annotations

from dataclasses import dataclass

from ..grid.face_index import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from ..math.vec3 import Vec3
from .aabb import AABB
from .ray import Ray


@dataclass(frozen=True)
class RayHitFace:
    """
    RayHitFace = (t_enter, point, face).

    I use this immutable record as the result carrier of `ray_aabb_face()`. The field `t_enter`
    stores the selected parametric intersection value, `point` stores the Euclidean point
    `ray.origin + ray.direction * t_enter`, and `face` stores the face index associated with that
    selected boundary event.

    If the ray starts outside the box and intersects it in the forward parametric direction, then
    `t_enter` is the entry parameter and `face` is the entry face. If the ray starts inside the box,
    `t_enter` is the exit parameter chosen by `ray_aabb_face()`, and `face` is the exit face.
    """
    t_enter: float
    point: Vec3
    face: int


def _enter_face_for_axis(axis: int, inv_dir: float) -> int:
    """
    enter_face(axis, inv_dir) =
        FACE_NEG_X,  if axis = 0 and inv_dir >= 0,
        FACE_POS_X,  if axis = 0 and inv_dir <  0,
        FACE_NEG_Y,  if axis = 1 and inv_dir >= 0,
        FACE_POS_Y,  if axis = 1 and inv_dir <  0,
        FACE_NEG_Z,  if axis = 2 and inv_dir >= 0,
        FACE_POS_Z,  if axis = 2 and inv_dir <  0.

    I map the axis that updates the near slab boundary to the face through which the ray enters the
    box along that axis. Because `inv_dir = 1.0 / d_comp`, the sign of `inv_dir` is the sign of the
    direction component itself. A non-negative inverse therefore selects the negative axis face as
    the near plane, while a negative inverse selects the positive axis face.

    I use this helper only inside `ray_aabb_face()` to annotate the current `tmin` boundary.
    """
    if axis == 0:
        return FACE_NEG_X if inv_dir >= 0.0 else FACE_POS_X
    if axis == 1:
        return FACE_NEG_Y if inv_dir >= 0.0 else FACE_POS_Y
    return FACE_NEG_Z if inv_dir >= 0.0 else FACE_POS_Z


def _exit_face_for_axis(axis: int, inv_dir: float) -> int:
    """
    exit_face(axis, inv_dir) =
        FACE_POS_X,  if axis = 0 and inv_dir >= 0,
        FACE_NEG_X,  if axis = 0 and inv_dir <  0,
        FACE_POS_Y,  if axis = 1 and inv_dir >= 0,
        FACE_NEG_Y,  if axis = 1 and inv_dir <  0,
        FACE_POS_Z,  if axis = 2 and inv_dir >= 0,
        FACE_NEG_Z,  if axis = 2 and inv_dir <  0.

    I map the axis that updates the far slab boundary to the face through which the ray exits the
    box along that axis. The sign logic is the complement of `_enter_face_for_axis()` because the
    far plane lies on the opposite side of the interval.

    I use this helper only inside `ray_aabb_face()` to annotate the current `tmax` boundary.
    """
    if axis == 0:
        return FACE_POS_X if inv_dir >= 0.0 else FACE_NEG_X
    if axis == 1:
        return FACE_POS_Y if inv_dir >= 0.0 else FACE_NEG_Y
    return FACE_POS_Z if inv_dir >= 0.0 else FACE_NEG_Z


def ray_aabb_face(ray: Ray, aabb: AABB) -> RayHitFace | None:
    """
    For each axis i in {x, y, z}:

        if abs(d_i) < 1e-12:
            reject if o_i < mn_i or o_i > mx_i
        else:
            inv_i = 1 / d_i
            t1_i = (mn_i - o_i) * inv_i
            t2_i = (mx_i - o_i) * inv_i
            swap(t1_i, t2_i) if t1_i > t2_i

    tmin = max_i t1_i over active axes
    tmax = min_i t2_i over active axes

    reject if tmin > tmax
    reject if tmax < 0

    t_enter =
        tmin,  if tmin >= 0,
        tmax,  otherwise.

    p = o + d * t_enter.

    I implement an axis-aligned slab intersection test with explicit face tracking. The working
    interval is initialized to the finite sentinels `tmin = -1e30` and `tmax = 1e30`, not to
    infinities. I then sweep the X, Y, and Z slabs, shrinking the admissible parametric interval by
    the near and far boundary values that each non-parallel axis induces.

    The parallel-axis rule is exact. If `abs(d_comp) < 1e-12`, I treat that axis as parallel to its
    slab planes. In that case I reject immediately when the origin component lies strictly outside
    the closed interval `[mn, mx]`. Boundary equality is accepted because the rejection test is
    `o_comp < mn or o_comp > mx`, not `<=` or `>=`.

    Face tracking follows the strict update inequalities already present in the code. I replace
    `tmin` and `enter_face` only when `t1 > tmin`, and I replace `tmax` and `exit_face` only when
    `t2 < tmax`. A tie at the same parametric boundary therefore does not overwrite the face already
    stored from an earlier axis.

    The return rule distinguishes outside hits from inside hits. If the final `tmin` is non-negative,
    I return the entering boundary. If the origin lies inside the box so that `tmin < 0` but
    `tmax >= 0`, I return the exiting boundary instead. The point field is then computed exactly as
    `o + d * t_enter`.

    I use this function in `build_system.py` while selecting the earliest hit among the pick AABBs of
    a block. That caller normalizes and non-zero-checks the direction before constructing the `Ray`.
    I do not duplicate that guard here. Consequently, the function's literal behavior must be stated
    narrowly: if every axis is treated as parallel and the origin lies inside the box, the finite
    sentinel initialization leaves `tmax = 1e30`, so the inside-return path yields `t_enter = 1e30`
    and `face = -1`. I do not repair that degenerate case inside this function.
    """
    d = ray.direction
    o = ray.origin

    tmin = -1e30
    tmax = 1e30
    enter_face: int = -1
    exit_face: int = -1

    for axis, (o_comp, d_comp, mn, mx) in enumerate(
        (
            (o.x, d.x, aabb.mn.x, aabb.mx.x),
            (o.y, d.y, aabb.mn.y, aabb.mx.y),
            (o.z, d.z, aabb.mn.z, aabb.mx.z),
        )
    ):
        if abs(d_comp) < 1e-12:
            if o_comp < mn or o_comp > mx:
                return None
            continue

        inv = 1.0 / d_comp
        t1 = (mn - o_comp) * inv
        t2 = (mx - o_comp) * inv

        if t1 > t2:
            t1, t2 = t2, t1

        if t1 > tmin:
            tmin = t1
            enter_face = _enter_face_for_axis(int(axis), float(inv))

        if t2 < tmax:
            tmax = t2
            exit_face = _exit_face_for_axis(int(axis), float(inv))

        if tmin > tmax:
            return None

    if tmax < 0.0:
        return None

    if tmin >= 0.0:
        t_enter = float(tmin)
        face = int(enter_face)
    else:
        t_enter = float(tmax)
        face = int(exit_face)

    p = o + d * float(t_enter)
    return RayHitFace(t_enter=float(t_enter), point=p, face=int(face))
