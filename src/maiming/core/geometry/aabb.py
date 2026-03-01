# FILE: src/maiming/core/geometry/aabb.py
from __future__ import annotations
from dataclasses import dataclass
from maiming.core.math.vec3 import Vec3

@dataclass(frozen=True)
class AABB:
    mn: Vec3
    mx: Vec3

    def intersects(self, o: "AABB") -> bool:
        return not (
            self.mx.x <= o.mn.x or self.mn.x >= o.mx.x or
            self.mx.y <= o.mn.y or self.mn.y >= o.mx.y or
            self.mx.z <= o.mn.z or self.mn.z >= o.mx.z
        )