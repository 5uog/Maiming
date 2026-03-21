# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
import numpy as np

def identity_matrix() -> np.ndarray:
    return np.identity(4, dtype=np.float32)

def translate_matrix(x: float, y: float, z: float) -> np.ndarray:
    matrix = identity_matrix()
    matrix[0, 3] = float(x)
    matrix[1, 3] = float(y)
    matrix[2, 3] = float(z)
    return matrix

def scale_matrix(x: float, y: float, z: float) -> np.ndarray:
    matrix = identity_matrix()
    matrix[0, 0] = float(x)
    matrix[1, 1] = float(y)
    matrix[2, 2] = float(z)
    return matrix

def rotate_x_rad_matrix(rad: float) -> np.ndarray:
    matrix = identity_matrix()
    c = math.cos(float(rad))
    s = math.sin(float(rad))
    matrix[1, 1] = float(c)
    matrix[1, 2] = float(-s)
    matrix[2, 1] = float(s)
    matrix[2, 2] = float(c)
    return matrix

def rotate_y_rad_matrix(rad: float) -> np.ndarray:
    matrix = identity_matrix()
    c = math.cos(float(rad))
    s = math.sin(float(rad))
    matrix[0, 0] = float(c)
    matrix[0, 2] = float(-s)
    matrix[2, 0] = float(s)
    matrix[2, 2] = float(c)
    return matrix

def rotate_z_rad_matrix(rad: float) -> np.ndarray:
    matrix = identity_matrix()
    c = math.cos(float(rad))
    s = math.sin(float(rad))
    matrix[0, 0] = float(c)
    matrix[0, 1] = float(-s)
    matrix[1, 0] = float(s)
    matrix[1, 1] = float(c)
    return matrix

def rotate_x_deg_matrix(deg: float) -> np.ndarray:
    return rotate_x_rad_matrix(math.radians(float(deg)))

def rotate_y_deg_matrix(deg: float) -> np.ndarray:
    return rotate_y_rad_matrix(math.radians(float(deg)))

def rotate_z_deg_matrix(deg: float) -> np.ndarray:
    return rotate_z_rad_matrix(math.radians(float(deg)))

def compose_matrices(*matrices: np.ndarray) -> np.ndarray:
    out = identity_matrix()
    for matrix in matrices:
        out = (out @ np.asarray(matrix, dtype=np.float32)).astype(np.float32)
    return out