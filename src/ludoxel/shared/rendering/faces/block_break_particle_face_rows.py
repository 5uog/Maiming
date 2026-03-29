# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from ...math.transform_matrices import compose_matrices, identity_matrix, scale_matrix, translate_matrix
from ...math.vec3 import Vec3
from ..render_snapshot import BlockBreakParticleRenderSampleDTO
from .face_row_utils import append_face_instance, empty_textured_face_rows, face_rows_from_buffers


def _billboard_basis(forward: Vec3) -> tuple[Vec3, Vec3, Vec3]:
    direction = forward.normalized()
    right = Vec3(0.0, 1.0, 0.0).cross(direction)
    if right.length() <= 1e-9:
        right = Vec3(1.0, 0.0, 0.0).cross(direction)
    if right.length() <= 1e-9:
        right = Vec3(1.0, 0.0, 0.0)
    right = right.normalized()
    up = direction.cross(right).normalized()
    return (right, up, direction)


def _rotation_from_basis(*, right: Vec3, up: Vec3, forward: Vec3) -> np.ndarray:
    matrix = identity_matrix()
    matrix[0, 0] = float(right.x)
    matrix[0, 1] = float(up.x)
    matrix[0, 2] = float(forward.x)
    matrix[1, 0] = float(right.y)
    matrix[1, 1] = float(up.y)
    matrix[1, 2] = float(forward.y)
    matrix[2, 0] = float(right.z)
    matrix[2, 1] = float(up.z)
    matrix[2, 2] = float(forward.z)
    return matrix


def build_block_break_particle_face_rows(*, samples: tuple[BlockBreakParticleRenderSampleDTO, ...], camera_forward: Vec3) -> tuple[np.ndarray, ...]:
    if not samples:
        return empty_textured_face_rows()

    right, up, forward = _billboard_basis(camera_forward)
    rotation = _rotation_from_basis(right=right, up=up, forward=forward)
    buffers: list[list[list[float]]] = [[] for _ in range(6)]

    for sample in samples:
        model = compose_matrices(translate_matrix(float(sample.x), float(sample.y), float(sample.z)), rotation, scale_matrix(float(sample.size), float(sample.size), 1.0), translate_matrix(0.0, 0.0, -0.5))
        append_face_instance(buffers, 4, model,(float(sample.u0), float(sample.v0), float(sample.u1), float(sample.v1)))

    return face_rows_from_buffers(buffers)
