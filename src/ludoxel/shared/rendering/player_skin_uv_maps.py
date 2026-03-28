# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ..math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z


def _skin_cube_uv_map(*, pos_x: tuple[float, float, float, float], neg_x: tuple[float, float, float, float], pos_y: tuple[float, float, float, float], neg_y: tuple[float, float, float, float], pos_z: tuple[float, float, float, float], neg_z: tuple[float, float, float, float]) -> dict[int, tuple[float, float, float, float]]:
    """I define U = {+X,-X,+Y,-Y,+Z,-Z} -> R^4, where each face key is mapped onto its skin-space pixel rectangle. I use this constructor to keep the arm and sleeve UV atlases algebraically explicit while avoiding repeated face-index bookkeeping."""
    return {FACE_POS_X: pos_x, FACE_NEG_X: neg_x, FACE_POS_Y: pos_y, FACE_NEG_Y: neg_y, FACE_POS_Z: pos_z, FACE_NEG_Z: neg_z}


def _rotate_uv_rect_180(px_rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """I define R180(u0,v0,u1,v1) = (u1,v1,u0,v0). I apply this involution when the skin face must be sampled with the orientation expected by the mesh convention rather than the raw texture-layout convention."""
    return (float(px_rect[2]), float(px_rect[3]), float(px_rect[0]), float(px_rect[1]))


def _uv_map_with_rotated_faces(uv_map: dict[int, tuple[float, float, float, float]], *faces: int) -> dict[int, tuple[float, float, float, float]]:
    """I define U'(f) = R180(U(f)) for every requested face f and U'(g) = U(g) otherwise. I use this selective reorientation to keep atlas data canonical while still matching the winding and face-local tangent conventions of the renderer."""
    out = {int(face_idx): tuple(rect) for face_idx, rect in uv_map.items()}
    for face_idx in faces:
        out[int(face_idx)] = _rotate_uv_rect_180(out[int(face_idx)])
    return out


RIGHT_ARM_BASE_UV_PX = _skin_cube_uv_map(pos_x=(40.0, 20.0, 44.0, 32.0), neg_x=(47.0, 20.0, 51.0, 32.0), pos_y=(44.0, 16.0, 47.0, 20.0), neg_y=(47.0, 16.0, 50.0, 20.0), pos_z=(44.0, 20.0, 47.0, 32.0), neg_z=(51.0, 20.0, 54.0, 32.0))
RIGHT_ARM_SLEEVE_UV_PX = _skin_cube_uv_map(pos_x=(40.0, 36.0, 44.0, 48.0), neg_x=(47.0, 36.0, 51.0, 48.0), pos_y=(44.0, 32.0, 47.0, 36.0), neg_y=(47.0, 32.0, 50.0, 36.0), pos_z=(44.0, 36.0, 47.0, 48.0), neg_z=(51.0, 36.0, 54.0, 48.0))
LEFT_ARM_BASE_UV_PX = _skin_cube_uv_map(pos_x=(32.0, 52.0, 36.0, 64.0), neg_x=(39.0, 52.0, 43.0, 64.0), pos_y=(36.0, 48.0, 39.0, 52.0), neg_y=(39.0, 48.0, 42.0, 52.0), pos_z=(36.0, 52.0, 39.0, 64.0), neg_z=(43.0, 52.0, 46.0, 64.0))
LEFT_ARM_SLEEVE_UV_PX = _skin_cube_uv_map(pos_x=(48.0, 52.0, 52.0, 64.0), neg_x=(55.0, 52.0, 59.0, 64.0), pos_y=(52.0, 48.0, 55.0, 52.0), neg_y=(55.0, 48.0, 58.0, 52.0), pos_z=(52.0, 52.0, 55.0, 64.0), neg_z=(59.0, 52.0, 62.0, 64.0))

SLIM_RIGHT_ARM_BASE_UV_PX = RIGHT_ARM_BASE_UV_PX
SLIM_RIGHT_ARM_SLEEVE_UV_PX = RIGHT_ARM_SLEEVE_UV_PX

VISUAL_RIGHT_ARM_BASE_UV_PX = _uv_map_with_rotated_faces(RIGHT_ARM_BASE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
VISUAL_RIGHT_ARM_SLEEVE_UV_PX = _uv_map_with_rotated_faces(RIGHT_ARM_SLEEVE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
VISUAL_LEFT_ARM_BASE_UV_PX = _uv_map_with_rotated_faces(LEFT_ARM_BASE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
VISUAL_LEFT_ARM_SLEEVE_UV_PX = _uv_map_with_rotated_faces(LEFT_ARM_SLEEVE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
