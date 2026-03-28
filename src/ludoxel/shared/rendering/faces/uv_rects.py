# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ...blocks.models.common import LocalBox
from ...math.scalars import clamp01f, lerpf
from ...math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_POS_X, FACE_POS_Y, FACE_POS_Z

UVRect = tuple[float, float, float, float]


def atlas_uv_rect(atlas: UVRect, u0: float, v0: float, u1: float, v1: float) -> UVRect:
    """I define U_atlas(u,v) by affine interpolation of the local rectangle (u0,v0,u1,v1) inside the parent atlas rectangle. I use this map as the primitive from which every face-local UV derivation in the renderer is built."""
    atlas_u0, atlas_v0, atlas_u1, atlas_v1 = atlas
    return (lerpf(atlas_u0, atlas_u1, clamp01f(u0)), lerpf(atlas_v0, atlas_v1, clamp01f(v0)), lerpf(atlas_u0, atlas_u1, clamp01f(u1)), lerpf(atlas_v0, atlas_v1, clamp01f(v1)))


def sub_uv_rect(atlas: UVRect, face_idx: int, box: LocalBox) -> UVRect:
    """I define U_face as the geometric sub-rectangle induced by the local-box extents on the requested voxel face. I use this default map for block families whose face texturing is fully determined by cuboid geometry alone."""
    if int(face_idx) == FACE_POS_X:
        u0, u1 = float(box.mn_z), float(box.mx_z)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    elif int(face_idx) == FACE_NEG_X:
        u0, u1 = float(box.mx_z), float(box.mn_z)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    elif int(face_idx) == FACE_POS_Y:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_z), float(box.mx_z)
    elif int(face_idx) == FACE_NEG_Y:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mx_z), float(box.mn_z)
    elif int(face_idx) == FACE_POS_Z:
        u0, u1 = float(box.mx_x), float(box.mn_x)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    else:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    return atlas_uv_rect(atlas, u0, v0, u1, v1)


def fence_gate_uv_rect(atlas: UVRect, face_idx: int, box: LocalBox) -> UVRect:
    """I define U_gate as the face-local UV selector specialized for fence-gate cuboids, whose front and back faces do not apply the same horizontal reversal rule as a full cube. I use this map to preserve the expected atlas orientation of narrow gate bars and crosspieces."""
    if int(face_idx) in (FACE_POS_X, FACE_NEG_X):
        u0, u1 = float(box.mn_z), float(box.mx_z)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    elif int(face_idx) in (FACE_POS_Y, FACE_NEG_Y):
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_z), float(box.mx_z)
    else:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    return atlas_uv_rect(atlas, u0, v0, u1, v1)
