# FILE: src/maiming/core/geometry/ray.py
from __future__ import annotations
from dataclasses import dataclass

from ..math.vec3 import Vec3

@dataclass(frozen=True)
class Ray:
    origin: Vec3
    direction: Vec3