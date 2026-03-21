# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ..math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from ..blocks.models.common import LocalBox

UVRect = tuple[float, float, float, float]

def _lerp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)

def _clamp01(x: float) -> float:
    value = float(x)
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value

def atlas_uv_rect(atlas: UVRect, u0: float, v0: float, u1: float, v1: float) -> UVRect:
    atlas_u0, atlas_v0, atlas_u1, atlas_v1 = atlas
    return (_lerp(atlas_u0, atlas_u1, _clamp01(u0)), _lerp(atlas_v0, atlas_v1, _clamp01(v0)), _lerp(atlas_u0, atlas_u1, _clamp01(u1)), _lerp(atlas_v0, atlas_v1, _clamp01(v1)))

def sub_uv_rect(atlas: UVRect, face_idx: int, box: LocalBox) -> UVRect:
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