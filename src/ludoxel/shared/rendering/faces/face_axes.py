# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ...blocks.models.common import LocalBox

FACE_EPSILON = 1e-7


def approx_eq(a: float, b: float) -> bool:
    """I define a ~= b iff |a - b| <= eps, where eps = FACE_EPSILON. I use this tolerance relation to stabilize face-boundary tests against float noise introduced by model decomposition and affine composition."""
    return abs(float(a) - float(b)) <= FACE_EPSILON


def face_touches_cell_boundary(face_idx: int, box: LocalBox) -> bool:
    """I define T(face, box) as the predicate that the requested box face lies on the unit-cell boundary associated with that face index. I use this boundary test to decide whether occlusion may depend on a neighboring voxel rather than only on intra-block geometry."""
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
    """I define R(face, box) as the 2D rectangle obtained by projecting the requested face onto its intrinsic coordinate plane. I use this rectangle as the canonical domain on which local and neighbor occlusion become pure cover problems."""
    fi = int(face_idx)

    if fi in (0, 1):
        return (float(box.mn_y), float(box.mx_y), float(box.mn_z), float(box.mx_z))
    if fi in (2, 3):
        return (float(box.mn_x), float(box.mx_x), float(box.mn_z), float(box.mx_z))

    return (float(box.mn_x), float(box.mx_x), float(box.mn_y), float(box.mx_y))
