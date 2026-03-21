# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
import numpy as np

from .vec3 import Vec3

def identity() -> np.ndarray:
    return np.identity(4, dtype=np.float32)

def perspective(fov_y_deg: float, aspect: float, z_near: float, z_far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fov_y_deg) * 0.5)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / max(float(aspect), 1e-9)
    m[1, 1] = f
    m[2, 2] = (z_far + z_near) / (z_near - z_far)
    m[2, 3] = (2.0 * z_far * z_near) / (z_near - z_far)
    m[3, 2] = -1.0
    return m

def ortho(left: float, right: float, bottom: float, top: float, z_near: float, z_far: float) -> np.ndarray:
    m = np.zeros((4, 4), dtype=np.float32)
    rl = max(right - left, 1e-9)
    tb = max(top - bottom, 1e-9)
    fn = max(z_far - z_near, 1e-9)

    m[0, 0] = 2.0 / rl
    m[1, 1] = 2.0 / tb
    m[2, 2] = -2.0 / fn
    m[3, 3] = 1.0

    m[0, 3] = -(right + left) / rl
    m[1, 3] = -(top + bottom) / tb
    m[2, 3] = -(z_far + z_near) / fn
    return m

def look_dir(eye: Vec3, forward: Vec3, up_hint: Vec3=Vec3(0.0, 1.0, 0.0)) -> np.ndarray:
    f = forward.normalized()
    r = up_hint.cross(f).normalized()
    u = f.cross(r).normalized()

    m = identity()
    m[0, 0], m[0, 1], m[0, 2] = r.x, r.y, r.z
    m[1, 0], m[1, 1], m[1, 2] = u.x, u.y, u.z
    m[2, 0], m[2, 1], m[2, 2] = -f.x, -f.y, -f.z

    m[0, 3] = -r.dot(eye)
    m[1, 3] = -u.dot(eye)
    m[2, 3] = f.dot(eye)
    return m

def mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a @ b).astype(np.float32)