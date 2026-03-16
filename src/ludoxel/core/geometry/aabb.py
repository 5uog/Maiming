# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/geometry/aabb.py
from __future__ import annotations

from dataclasses import dataclass

from ..math.vec3 import Vec3


@dataclass(frozen=True)
class AABB:
    """
    A = [mn.x, mx.x] x [mn.y, mx.y] x [mn.z, mx.z].

    I use this immutable record as the axis-aligned box carrier of my geometry layer. The type stores
    only two endpoint vectors, `mn` and `mx`. I do not enforce `mn <= mx` component-wise, and I do
    not normalize, clamp, or reorder the bounds at construction time. Any ordering invariant is a
    caller-side responsibility.

    I use this type in collision resolution, block-shape translation, placement rejection, and
    ray-box intersection. In `domain.blocks.models.api` I construct world-space block boxes from
    local boxes, in `collision_system.py` I use instances of this type as the moving and static
    collision volumes, and in `intersection.py` I consume it as the target of the slab intersection
    test.
    """
    mn: Vec3
    mx: Vec3

    def intersects(self, o: "AABB") -> bool:
        """
        intersects(a, b) =
            not (
                a.mx.x <= b.mn.x or a.mn.x >= b.mx.x or
                a.mx.y <= b.mn.y or a.mn.y >= b.mx.y or
                a.mx.z <= b.mn.z or a.mn.z >= b.mx.z
            ).

        I implement strict overlap on all three axes by the exact negated-separation test written
        here. This has a precise geometric consequence: mere boundary contact does not count as an
        intersection. If the two boxes only touch on a face, an edge, or a corner, at least one of
        the ordered comparisons becomes true and the method returns `False`.

        I rely on this strictness in `collision_system.py`, where contact resolution and support
        probing distinguish penetration from mere adjacency, and in `placement_policy.py`, where I
        reject block placements only when the candidate collision box intrudes into the player's box
        rather than merely touching it.
        """
        return not (
            self.mx.x <= o.mn.x or
            self.mn.x >= o.mx.x or
            self.mx.y <= o.mn.y or
            self.mn.y >= o.mx.y or
            self.mx.z <= o.mn.z or
            self.mn.z >= o.mx.z
        )
