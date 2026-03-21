# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from ...math import mat4
from ...math.vec3 import Vec3
from .gl_renderer_params import ShadowParams, SunParams

def _snap(value: float, quantum: float) -> float:
    q = float(max(1e-9, float(quantum)))
    return float(np.round(float(value) / q) * q)

def _light_up_hint(light_forward: Vec3) -> Vec3:
    world_up = Vec3(0.0, 1.0, 0.0)
    if abs(light_forward.dot(world_up)) < 0.999:
        return world_up
    return Vec3(0.0, 0.0, 1.0) if abs(float(light_forward.z)) < 0.999 else Vec3(1.0, 0.0, 0.0)

def compute_light_view_proj(*, center: Vec3, sun_dir: Vec3, sun: SunParams, shadow: ShadowParams, shadow_size: int) -> np.ndarray:
    sdir = sun_dir.normalized()
    light_forward = Vec3(-sdir.x, -sdir.y, -sdir.z).normalized()
    up_hint = _light_up_hint(light_forward)

    anchor_center = Vec3(float(center.x), float(center.y), float(center.z))

    if bool(shadow.stabilize):
        ld = float(sun.light_distance)
        probe_eye = Vec3(float(center.x) + float(sdir.x) * ld, float(center.y) + float(sdir.y) * ld, float(center.z) + float(sdir.z) * ld)
        probe_view = mat4.look_dir(probe_eye, light_forward, up_hint).astype(np.float32, copy=False)

        right = Vec3(float(probe_view[0, 0]), float(probe_view[0, 1]), float(probe_view[0, 2]))
        up = Vec3(float(probe_view[1, 0]), float(probe_view[1, 1]), float(probe_view[1, 2]))
        light_axis = Vec3(float(probe_view[2, 0]), float(probe_view[2, 1]), float(probe_view[2, 2]))

        r = float(sun.ortho_radius)
        s = float(max(1, int(shadow_size)))
        texel = (2.0 * r) / s

        cx = right.dot(center)
        cy = up.dot(center)
        cz = light_axis.dot(center)

        sx = _snap(float(cx), float(texel))
        sy = _snap(float(cy), float(texel))

        anchor_center = (right * float(sx)) + (up * float(sy)) + (light_axis * float(cz))

    ld = float(sun.light_distance)
    light_pos = Vec3(float(anchor_center.x) + float(sdir.x) * ld, float(anchor_center.y) + float(sdir.y) * ld, float(anchor_center.z) + float(sdir.z) * ld)

    view = mat4.look_dir(light_pos, light_forward, up_hint)
    r = float(sun.ortho_radius)
    proj = mat4.ortho(-r, r, -r, r, float(sun.ortho_near), float(sun.ortho_far))
    return mat4.mul(proj, view).astype(np.float32)