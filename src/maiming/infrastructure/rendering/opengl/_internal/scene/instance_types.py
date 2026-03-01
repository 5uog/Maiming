# FILE: src/maiming/infrastructure/rendering/opengl/scene/instance_types.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class BlockFaceInstanceGPU:
    mn_x: float
    mn_y: float
    mn_z: float
    mx_x: float
    mx_y: float
    mx_z: float
    u0: float
    v0: float
    u1: float
    v1: float
    shade: float = 1.0
    uv_rot: float = 0.0

@dataclass(frozen=True)
class ShadowCasterGPU:
    cx: float
    cy: float
    cz: float
    sx: float
    sy: float
    sz: float