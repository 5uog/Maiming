# FILE: src/maiming/domain/systems/movement_system.py
from __future__ import annotations

from dataclasses import dataclass
import math

from maiming.core.math.vec3 import Vec3, clampf
from maiming.core.math.smoothing import exp_alpha
from maiming.domain.entities.player_entity import PlayerEntity
from maiming.domain.config.movement_params import MovementParams, DEFAULT_MOVEMENT_PARAMS

@dataclass(frozen=True)
class MoveInput:
    forward: float
    strafe: float

    sprint: bool
    crouch: bool

    jump_pulse: bool
    jump_held: bool

    yaw_delta_deg: float
    pitch_delta_deg: float

def _basis_from_yaw_deg(yaw_deg: float) -> tuple[Vec3, Vec3]:
    yaw = math.radians(float(yaw_deg))
    fwd = Vec3(-math.sin(yaw), 0.0, math.cos(yaw))
    rgt = Vec3(math.cos(yaw), 0.0, math.sin(yaw))
    return fwd, rgt

def _wish_dir(player: PlayerEntity, forward: float, strafe: float) -> Vec3:
    fwd, rgt = _basis_from_yaw_deg(player.yaw_deg)
    v = (fwd * float(forward)) + (rgt * float(strafe))
    if v.length() <= 1e-9:
        return Vec3(0.0, 0.0, 0.0)
    return v.normalized()

def step_bedrock(
    player: PlayerEntity,
    inp: MoveInput,
    dt: float,
    params: MovementParams = DEFAULT_MOVEMENT_PARAMS,
) -> None:
    player.yaw_deg += float(inp.yaw_delta_deg)
    player.pitch_deg += float(inp.pitch_delta_deg)
    player.clamp_pitch()

    f = clampf(inp.forward, -1.0, 1.0)
    s = clampf(inp.strafe, -1.0, 1.0)

    wish = _wish_dir(player, f, s)

    want_sprint = bool(inp.sprint) and (float(f) > 1e-6) and (not bool(inp.crouch))
    max_speed = float(params.sprint_speed) if want_sprint else float(params.walk_speed)

    if bool(inp.crouch):
        max_speed *= float(params.crouch_mult)

    if wish.length() <= 1e-9:
        target = Vec3(0.0, 0.0, 0.0)
    else:
        target = Vec3(wish.x * max_speed, 0.0, wish.z * max_speed)

    vx, vy, vz = float(player.velocity.x), float(player.velocity.y), float(player.velocity.z)

    if bool(player.on_ground):
        a = exp_alpha(float(params.accel_ground), dt)
    else:
        a = exp_alpha(float(params.accel_air), dt)

    vx = vx + (float(target.x) - vx) * a
    vz = vz + (float(target.z) - vz) * a

    if bool(player.on_ground):
        if vy < 0.0:
            vy = 0.0

        if bool(inp.jump_pulse):
            vy = float(params.jump_v0)
            player.on_ground = False

            if want_sprint and wish.length() > 1e-9:
                bx = float(wish.x) * float(params.sprint_jump_boost)
                bz = float(wish.z) * float(params.sprint_jump_boost)
                vx += bx
                vz += bz
        else:
            if wish.length() <= 1e-9:
                stop_v = 0.03
                if abs(float(vx)) < stop_v:
                    vx = 0.0
                if abs(float(vz)) < stop_v:
                    vz = 0.0
    else:
        vy = vy - float(params.gravity) * float(dt)
        if vy < -float(params.fall_speed_max):
            vy = -float(params.fall_speed_max)

    player.velocity = Vec3(vx, vy, vz)