# FILE: src/maiming/domain/entities/player_entity.py
from __future__ import annotations

from dataclasses import dataclass

from maiming.core.math.vec3 import Vec3, clampf
from maiming.core.geometry.aabb import AABB
from maiming.core.math.view_angles import forward_from_yaw_pitch_deg

@dataclass
class PlayerEntity:
    position: Vec3
    velocity: Vec3
    yaw_deg: float
    pitch_deg: float

    on_ground: bool = False

    width: float = 0.6
    height: float = 1.8

    eye_height: float = 1.62
    crouch_eye_drop: float = 0.25
    crouch_eye_offset: float = 0.0

    hold_jump_queued: bool = False

    auto_jump_pending: bool = False
    auto_jump_start_y: float = 0.0
    auto_jump_cooldown_s: float = 0.0

    def eye_pos(self) -> Vec3:
        return Vec3(self.position.x, self.position.y + (self.eye_height - self.crouch_eye_offset), self.position.z)

    def view_forward(self) -> Vec3:
        return forward_from_yaw_pitch_deg(self.yaw_deg, self.pitch_deg)

    def clamp_pitch(self) -> None:
        self.pitch_deg = clampf(self.pitch_deg, -89.5, 89.5)

    def aabb_at(self, pos: Vec3) -> AABB:
        hw = float(self.width) * 0.5
        mn = Vec3(pos.x - hw, pos.y, pos.z - hw)
        mx = Vec3(pos.x + hw, pos.y + float(self.height), pos.z + hw)
        return AABB(mn=mn, mx=mx)