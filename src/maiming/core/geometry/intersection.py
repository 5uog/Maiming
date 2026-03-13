# FILE: src/maiming/core/geometry/intersection.py
from __future__ import annotations
from dataclasses import dataclass

from ..grid.face_index import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from ..math.vec3 import Vec3
from .aabb import AABB
from .ray import Ray

@dataclass(frozen=True)
class RayHitFace:
    t_enter: float
    point: Vec3
    face: int

def _enter_face_for_axis(axis: int, inv_dir: float) -> int:
    if axis == 0:
        return FACE_NEG_X if inv_dir >= 0.0 else FACE_POS_X
    if axis == 1:
        return FACE_NEG_Y if inv_dir >= 0.0 else FACE_POS_Y
    return FACE_NEG_Z if inv_dir >= 0.0 else FACE_POS_Z

def _exit_face_for_axis(axis: int, inv_dir: float) -> int:
    if axis == 0:
        return FACE_POS_X if inv_dir >= 0.0 else FACE_NEG_X
    if axis == 1:
        return FACE_POS_Y if inv_dir >= 0.0 else FACE_NEG_Y
    return FACE_POS_Z if inv_dir >= 0.0 else FACE_NEG_Z

def ray_aabb_face(ray: Ray, aabb: AABB) -> RayHitFace | None:
    d = ray.direction
    o = ray.origin

    tmin = -1e30
    tmax = 1e30
    enter_face: int = -1
    exit_face: int = -1

    for axis, (o_comp, d_comp, mn, mx) in enumerate(((o.x, d.x, aabb.mn.x, aabb.mx.x), (o.y, d.y, aabb.mn.y, aabb.mx.y), (o.z, d.z, aabb.mn.z, aabb.mx.z))):
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