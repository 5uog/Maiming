# FILE: src/maiming/core/math/view_angles.py
from __future__ import annotations

import math

from maiming.core.math.vec3 import Vec3

def forward_from_yaw_pitch_deg(yaw_deg: float, pitch_deg: float) -> Vec3:
    yaw = math.radians(float(yaw_deg))
    pitch = math.radians(float(pitch_deg))

    cy = math.cos(yaw)
    sy = math.sin(yaw)
    cp = math.cos(pitch)
    sp = math.sin(pitch)

    return Vec3(-sy * cp, -sp, cy * cp).normalized()

def sun_dir_from_az_el_deg(azimuth_deg: float, elevation_deg: float) -> Vec3:
    az = math.radians(float(azimuth_deg))
    el = math.radians(float(elevation_deg))

    x = math.cos(el) * math.sin(az)
    y = math.sin(el)
    z = math.cos(el) * math.cos(az)

    return Vec3(x, y, z).normalized()