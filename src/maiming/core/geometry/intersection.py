# FILE: src/maiming/core/geometry/intersection.py
from __future__ import annotations
from dataclasses import dataclass
from maiming.core.math.vec3 import Vec3
from maiming.core.geometry.aabb import AABB
from maiming.core.geometry.ray import Ray

@dataclass(frozen=True)
class RayHit:
    t_enter: float
    point: Vec3

def ray_aabb(ray: Ray, aabb: AABB) -> RayHit | None:
    d = ray.direction
    o = ray.origin

    tmin = -1e30
    tmax = 1e30

    for o_comp, d_comp, mn, mx in (
        (o.x, d.x, aabb.mn.x, aabb.mx.x),
        (o.y, d.y, aabb.mn.y, aabb.mx.y),
        (o.z, d.z, aabb.mn.z, aabb.mx.z),
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
        tmin = max(tmin, t1)
        tmax = min(tmax, t2)
        if tmin > tmax:
            return None

    if tmax < 0.0:
        return None
    t_enter = tmin if tmin >= 0.0 else tmax
    p = o + d * t_enter
    return RayHit(t_enter=t_enter, point=p)