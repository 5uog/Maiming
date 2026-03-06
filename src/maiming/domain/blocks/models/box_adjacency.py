# FILE: src/maiming/domain/blocks/models/box_adjacency.py
from __future__ import annotations

from maiming.domain.blocks.models.common import LocalBox

_EPS = 1e-7

def _eq(a: float, b: float, eps: float = _EPS) -> bool:
    return abs(float(a) - float(b)) <= float(eps)

def internal_face_mask(boxes: list[LocalBox]) -> set[tuple[int, int]]:
    internal: set[tuple[int, int]] = set()

    for i, a in enumerate(boxes):
        for j, b in enumerate(boxes):
            if i == j:
                continue

            if _eq(a.mx_x, b.mn_x):
                if _eq(a.mn_y, b.mn_y) and _eq(a.mx_y, b.mx_y) and _eq(a.mn_z, b.mn_z) and _eq(a.mx_z, b.mx_z):
                    internal.add((i, 0))
                    internal.add((j, 1))

            if _eq(a.mn_x, b.mx_x):
                if _eq(a.mn_y, b.mn_y) and _eq(a.mx_y, b.mx_y) and _eq(a.mn_z, b.mn_z) and _eq(a.mx_z, b.mx_z):
                    internal.add((i, 1))
                    internal.add((j, 0))

            if _eq(a.mx_y, b.mn_y):
                if _eq(a.mn_x, b.mn_x) and _eq(a.mx_x, b.mx_x) and _eq(a.mn_z, b.mn_z) and _eq(a.mx_z, b.mx_z):
                    internal.add((i, 2))
                    internal.add((j, 3))

            if _eq(a.mn_y, b.mx_y):
                if _eq(a.mn_x, b.mn_x) and _eq(a.mx_x, b.mx_x) and _eq(a.mn_z, b.mn_z) and _eq(a.mx_z, b.mx_z):
                    internal.add((i, 3))
                    internal.add((j, 2))

            if _eq(a.mx_z, b.mn_z):
                if _eq(a.mn_x, b.mn_x) and _eq(a.mx_x, b.mx_x) and _eq(a.mn_y, b.mn_y) and _eq(a.mx_y, b.mx_y):
                    internal.add((i, 4))
                    internal.add((j, 5))

            if _eq(a.mn_z, b.mx_z):
                if _eq(a.mn_x, b.mn_x) and _eq(a.mx_x, b.mx_x) and _eq(a.mn_y, b.mn_y) and _eq(a.mx_y, b.mx_y):
                    internal.add((i, 5))
                    internal.add((j, 4))

    return internal