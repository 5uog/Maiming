# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/math/view_angles.py
from __future__ import annotations

import math

from .vec3 import Vec3


def forward_from_yaw_pitch_deg(yaw_deg: float, pitch_deg: float) -> Vec3:
    """
    yaw = radians(yaw_deg)
    pitch = radians(pitch_deg)

    d_raw = (
        -sin(yaw)*cos(pitch),
        -sin(pitch),
        cos(yaw)*cos(pitch)
    )

    d = normalize(d_raw).

    I construct the forward viewing direction from yaw and pitch by this exact component map. 
    After converting the supplied angles from degrees to radians, I evaluate the trigonometric 
    components and pass the resulting vector through `Vec3.normalized()` before returning it.

    The sign convention is fixed and exact. At `yaw_deg = 0` and `pitch_deg = 0`, the ideal raw
    direction is `(0, 0, 1)`, namely positive Z. Increasing yaw rotates the horizontal heading
    toward negative X because the X component is `-sin(yaw)*cos(pitch)`. Increasing pitch rotates
    the direction toward negative Y because the Y component is `-sin(pitch)`.

    In exact real arithmetic the raw vector is already unit length for all finite angles, since

        (-sin(yaw)*cos(pitch))^2 + (-sin(pitch))^2 + (cos(yaw)*cos(pitch))^2
        = cos(pitch)^2 * (sin(yaw)^2 + cos(yaw)^2) + sin(pitch)^2
        = 1.

    The terminal normalization therefore serves chiefly as a uniform postcondition convention together 
    with the module-wide degeneracy rule implemented by `Vec3.normalized()`. It is not mathematically 
    required in the ideal trigonometric model, but it does make this constructor obey the same return 
    discipline as the rest of the direction-building layer.

    I use this function wherever yaw and pitch must be converted into an actual direction vector,
    including player view reconstruction in `player_entity.py`, render-camera forward construction in
    `frame_pipeline.py`, effective-camera reconstruction in `gl_viewport_widget.py`, and
    selection-ray generation in `viewport_selection_state.py`.
    """
    yaw = math.radians(float(yaw_deg))
    pitch = math.radians(float(pitch_deg))

    cy = math.cos(yaw)
    sy = math.sin(yaw)
    cp = math.cos(pitch)
    sp = math.sin(pitch)

    return Vec3(-sy * cp, -sp, cy * cp).normalized()


def sun_dir_from_az_el_deg(azimuth_deg: float, elevation_deg: float) -> Vec3:
    """
    az = radians(azimuth_deg)
    el = radians(elevation_deg)

    d_raw = (
        cos(el)*sin(az),
        sin(el),
        cos(el)*cos(az)
    )

    d = normalize(d_raw).

    I construct a direction vector from azimuth and elevation by this exact spherical-style component
    map and then normalize the result through `Vec3.normalized()` before return.

    The coordinate convention is explicit. At `azimuth_deg = 0` and `elevation_deg = 0`, the ideal
    raw direction is `(0, 0, 1)`, namely positive Z on the horizontal plane. At fixed zero
    elevation, increasing azimuth rotates the direction from positive Z toward positive X.
    Increasing elevation raises the direction toward positive Y, and at `elevation_deg = 90` the
    ideal direction is `(0, 1, 0)` independently of azimuth.

    As with `forward_from_yaw_pitch_deg()`, the raw formula is already unit length in exact arithmetic:

        (cos(el)*sin(az))^2 + sin(el)^2 + (cos(el)*cos(az))^2
        = cos(el)^2 * (sin(az)^2 + cos(az)^2) + sin(el)^2
        = 1.

    The terminal normalization is therefore chiefly a consistency device and a local robustness step
    rather than a mathematically necessary rescaling in the ideal model.

    I use this function in `render_state.py` to convert user-facing sun azimuth and elevation
    settings into the renderer's stored `sun_dir` vector.
    """
    az = math.radians(float(azimuth_deg))
    el = math.radians(float(elevation_deg))

    x = math.cos(el) * math.sin(az)
    y = math.sin(el)
    z = math.cos(el) * math.cos(az)

    return Vec3(x, y, z).normalized()
