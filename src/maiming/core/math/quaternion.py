# FILE: src/maiming/core/math/quaternion.py
from __future__ import annotations
from dataclasses import dataclass
import math
from maiming.core.math.vec3 import Vec3

@dataclass(frozen=True)
class Quaternion:
    w: float
    x: float
    y: float
    z: float

    @staticmethod
    def from_yaw_pitch(yaw_rad: float, pitch_rad: float) -> "Quaternion":
        cy = math.cos(yaw_rad * 0.5)
        sy = math.sin(yaw_rad * 0.5)
        cp = math.cos(pitch_rad * 0.5)
        sp = math.sin(pitch_rad * 0.5)

        w = cy * cp
        x = sp * cy
        y = sy * cp
        z = -sy * sp
        return Quaternion(w, x, y, z)

    def rotate(self, v: Vec3) -> Vec3:
        qx, qy, qz, qw = self.x, self.y, self.z, self.w
        vx, vy, vz = v.x, v.y, v.z

        tx = 2.0 * (qy * vz - qz * vy)
        ty = 2.0 * (qz * vx - qx * vz)
        tz = 2.0 * (qx * vy - qy * vx)

        rx = vx + qw * tx + (qy * tz - qz * ty)
        ry = vy + qw * ty + (qz * tx - qx * tz)
        rz = vz + qw * tz + (qx * ty - qy * tx)
        return Vec3(rx, ry, rz)