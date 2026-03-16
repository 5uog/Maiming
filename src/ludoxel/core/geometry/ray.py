# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/geometry/ray.py
from __future__ import annotations

from dataclasses import dataclass

from ..math.vec3 import Vec3


@dataclass(frozen=True)
class Ray:
    """
    r(t) = origin + direction * t.

    I use this immutable record as the ray carrier of my geometry layer. The type stores only an
    origin point and a direction vector. I do not normalize the direction, and I do not constrain
    the intended parameter domain at the type level. Any convention such as `t >= 0`, unit-length
    direction, or finite components belongs to the caller and to the consuming algorithm.

    I construct this type in `build_system.py` before ray-AABB intersection tests, and I consume it
    in `intersection.py`. The class itself is deliberately policy-free.
    """
    origin: Vec3
    direction: Vec3
