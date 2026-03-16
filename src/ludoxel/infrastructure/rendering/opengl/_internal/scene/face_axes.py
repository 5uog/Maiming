# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/scene/face_axes.py
from __future__ import annotations

from ......domain.blocks.models.common import LocalBox

_EPS = 1e-7


def approx_eq(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= _EPS


def face_touches_cell_boundary(face_idx: int, box: LocalBox) -> bool:
    fi = int(face_idx)

    if fi == 0:
        return approx_eq(float(box.mx_x), 1.0)
    if fi == 1:
        return approx_eq(float(box.mn_x), 0.0)
    if fi == 2:
        return approx_eq(float(box.mx_y), 1.0)
    if fi == 3:
        return approx_eq(float(box.mn_y), 0.0)
    if fi == 4:
        return approx_eq(float(box.mx_z), 1.0)
    return approx_eq(float(box.mn_z), 0.0)


def face_rect(face_idx: int, box: LocalBox) -> tuple[float, float, float, float]:
    fi = int(face_idx)

    if fi in (0, 1):
        return (float(box.mn_y), float(box.mx_y), float(box.mn_z), float(box.mx_z))
    if fi in (2, 3):
        return (float(box.mn_x), float(box.mx_x), float(box.mn_z), float(box.mx_z))

    return (float(box.mn_x), float(box.mx_x), float(box.mn_y), float(box.mx_y))
