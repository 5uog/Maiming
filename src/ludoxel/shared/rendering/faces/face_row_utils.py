# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ...blocks.models.common import LocalBox
from ...math.transform_matrices import compose_matrices, scale_matrix, translate_matrix
from .uv_rects import UVRect, fence_gate_uv_rect, sub_uv_rect


def empty_textured_face_rows() -> tuple[np.ndarray, ...]:
    """I define E_i = 0_(0x20) for each face index i in {0,...,5}. This constructor gives every textured-face pipeline the same canonical empty payload shape, dtype, and face ordering."""
    return tuple(np.zeros((0, 20), dtype=np.float32) for _ in range(6))


def append_face_instance(buffers: list[list[list[float]]], face_idx: int, model: np.ndarray, uv_rect: UVRect) -> None:
    """I encode a face instance as r = vec(M[0:16], u0, v0, u1, v1) in R^20, where M is the flattened 4x4 model matrix and (u0,v0,u1,v1) is the texture rectangle. I append r into the buffer selected by face_idx."""
    row = list(np.asarray(model, dtype=np.float32).reshape(16))
    row.extend([float(uv_rect[0]), float(uv_rect[1]), float(uv_rect[2]), float(uv_rect[3])])
    buffers[int(face_idx)].append(row)


def face_rows_from_buffers(buffers: list[list[list[float]]]) -> tuple[np.ndarray, ...]:
    """I realize each face buffer B_i as an array A_i in R^(n_i x 20), with A_i = 0_(0x20) when n_i = 0. This map is the terminal packing step that normalizes all textured-face producers onto the renderer input contract."""
    return tuple(np.asarray(face_rows, dtype=np.float32) if face_rows else np.zeros((0, 20), dtype=np.float32) for face_rows in buffers)


def uv_rect_from_pixels(texture_uv: UVRect, px_rect: tuple[float, float, float, float], *, texture_size_px: float = 16.0) -> UVRect:
    """I define U'(p) = U0 + (U1 - U0) * p / S componentwise on pixel-space rectangle endpoints, where S is the local texture span in pixels. I use this affine rescaling when a box face consumes an explicit per-face pixel rectangle inside the parent atlas tile."""
    u0_a, v0_a, u1_a, v1_a = texture_uv
    px0, py0, px1, py1 = px_rect
    scale = max(float(texture_size_px), 1.0)
    return (
        float(u0_a + (u1_a - u0_a) * (float(px0) / scale)),
        float(v0_a + (v1_a - v0_a) * (float(py0) / scale)),
        float(u0_a + (u1_a - u0_a) * (float(px1) / scale)),
        float(v0_a + (v1_a - v0_a) * (float(py1) / scale)),
    )


def skin_uv_rect(px_rect: tuple[float, float, float, float], *, width: int, height: int) -> UVRect:
    """I define S(px0,py0,px1,py1) = (px0/W, 1 - py1/H, px1/W, 1 - py0/H), which converts image-space rectangles with top-left origin into OpenGL UV space with bottom-left origin. I use this map for player-skin cuboids and first-person arm quads."""
    px0, py0, px1, py1 = px_rect
    w = max(1.0, float(width))
    h = max(1.0, float(height))
    return (float(px0) / w, 1.0 - float(py1) / h, float(px1) / w, 1.0 - float(py0) / h)


def atlas_face_uv(texture_uv: UVRect, face_idx: int, box: LocalBox, *, kind: str | None = None, face_uv_pixels: Mapping[int, tuple[float, float, float, float]] | None = None) -> UVRect:
    """I define U_face as a three-branch selector. I first honor an explicit pixel rectangle when face_uv_pixels fixes one for the requested face, I then apply the fence-gate-specific remapping when the kind and uv_hint require it, and I otherwise fall back to the geometric sub-rectangle induced by the local box extents."""
    if face_uv_pixels is not None:
        px_rect = face_uv_pixels.get(int(face_idx))
        if px_rect is not None:
            return uv_rect_from_pixels(texture_uv, px_rect)

    normalized_kind = "" if kind is None else str(kind).strip().lower()
    if normalized_kind == "fence_gate" and bool(box.uv_hint):
        return fence_gate_uv_rect(texture_uv, int(face_idx), box)
    return sub_uv_rect(texture_uv, int(face_idx), box)


def model_matrix_for_local_box(parent_transform: np.ndarray, box: LocalBox) -> np.ndarray:
    """I define M_box = M_parent * T(c_x,c_y,c_z) * S(s_x,s_y,s_z), where c = (mn + mx)/2 and s = mx - mn componentwise. This is the canonical local-box instance transform used by held blocks, player model quads, and other cuboid-derived renderables."""
    center_x = 0.5 * (float(box.mn_x) + float(box.mx_x))
    center_y = 0.5 * (float(box.mn_y) + float(box.mx_y))
    center_z = 0.5 * (float(box.mn_z) + float(box.mx_z))
    size_x = float(box.mx_x) - float(box.mn_x)
    size_y = float(box.mx_y) - float(box.mn_y)
    size_z = float(box.mx_z) - float(box.mn_z)
    return compose_matrices(parent_transform, translate_matrix(center_x, center_y, center_z), scale_matrix(size_x, size_y, size_z))
