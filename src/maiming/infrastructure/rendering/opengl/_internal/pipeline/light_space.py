# FILE: src/maiming/infrastructure/rendering/opengl/_internal/pipeline/light_space.py
from __future__ import annotations

import numpy as np

from maiming.core.math.vec3 import Vec3
from maiming.core.math import mat4
from ...facade.gl_renderer_params import SunParams, ShadowParams

def compute_light_view_proj(
    *,
    center: Vec3,
    sun_dir: Vec3,
    sun: SunParams,
    shadow: ShadowParams,
    shadow_size: int,
) -> np.ndarray:
    sdir = sun_dir.normalized()
    light_forward = Vec3(-sdir.x, -sdir.y, -sdir.z).normalized()

    ld = float(sun.light_distance)
    light_pos = Vec3(
        float(center.x) + float(sdir.x) * ld,
        float(center.y) + float(sdir.y) * ld,
        float(center.z) + float(sdir.z) * ld,
    )

    view = mat4.look_dir(light_pos, light_forward)

    r = float(sun.ortho_radius)
    proj = mat4.ortho(-r, r, -r, r, float(sun.ortho_near), float(sun.ortho_far))

    if bool(shadow.stabilize):
        c4 = np.array([float(center.x), float(center.y), float(center.z), 1.0], dtype=np.float32)
        ls = (view @ c4).astype(np.float32)

        s = float(max(1, int(shadow_size)))
        texel = (2.0 * r) / s

        snap_x = np.round(float(ls[0]) / texel) * texel
        snap_y = np.round(float(ls[1]) / texel) * texel

        dx = float(snap_x) - float(ls[0])
        dy = float(snap_y) - float(ls[1])

        view = view.copy().astype(np.float32)
        view[0, 3] += dx
        view[1, 3] += dy

    return mat4.mul(proj, view).astype(np.float32)