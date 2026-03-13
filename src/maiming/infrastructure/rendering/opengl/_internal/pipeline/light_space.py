# FILE: src/maiming/infrastructure/rendering/opengl/_internal/pipeline/light_space.py
from __future__ import annotations
import numpy as np

from ......core.math.vec3 import Vec3
from ......core.math import mat4
from ...facade.gl_renderer_params import SunParams, ShadowParams

def _snap(value: float, quantum: float) -> float:
    q = float(max(1e-9, float(quantum)))
    return float(np.round(float(value) / q) * q)

def compute_light_view_proj(*, center: Vec3, sun_dir: Vec3, sun: SunParams, shadow: ShadowParams, shadow_size: int) -> np.ndarray:
    sdir = sun_dir.normalized()
    light_forward = Vec3(-sdir.x, -sdir.y, -sdir.z).normalized()

    anchor_center = Vec3(float(center.x), float(center.y), float(center.z))

    if bool(shadow.stabilize):
        ld = float(sun.light_distance)
        probe_eye = Vec3(float(center.x) + float(sdir.x) * ld, float(center.y) + float(sdir.y) * ld, float(center.z) + float(sdir.z) * ld)
        probe_view = mat4.look_dir(probe_eye, light_forward).astype(np.float32, copy=False)

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

    view = mat4.look_dir(light_pos, light_forward)
    r = float(sun.ortho_radius)
    proj = mat4.ortho(-r, r, -r, r, float(sun.ortho_near), float(sun.ortho_far))
    return mat4.mul(proj, view).astype(np.float32)