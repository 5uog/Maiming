# FILE: src/maiming/presentation/config/pause_overlay_params.py
from __future__ import annotations

from dataclasses import dataclass

from maiming.application.session.session_settings import SessionSettings

@dataclass(frozen=True)
class PauseOverlayParams:
    fov_min: int = int(SessionSettings.FOV_MIN)
    fov_max: int = int(SessionSettings.FOV_MAX)

    sens_milli_min: int = 1
    sens_milli_max: int = 300
    sens_scale: float = 1000.0

    sens_min: float = float(SessionSettings.SENS_MIN)
    sens_max: float = float(SessionSettings.SENS_MAX)

    sun_az_min: int = 0
    sun_az_max: int = 360
    sun_el_min: int = 0
    sun_el_max: int = 90

    render_dist_min: int = 2
    render_dist_max: int = 16

    gravity_milli_min: int = int(SessionSettings.GRAVITY_MIN * 100.0)
    gravity_milli_max: int = int(SessionSettings.GRAVITY_MAX * 100.0)
    gravity_scale: float = 100.0
    gravity_decimals: int = 2

    walk_speed_milli_min: int = int(SessionSettings.WALK_SPEED_MIN * 1000.0)
    walk_speed_milli_max: int = int(SessionSettings.WALK_SPEED_MAX * 1000.0)
    walk_speed_scale: float = 1000.0
    walk_speed_decimals: int = 3

    sprint_speed_milli_min: int = int(SessionSettings.SPRINT_SPEED_MIN * 1000.0)
    sprint_speed_milli_max: int = int(SessionSettings.SPRINT_SPEED_MAX * 1000.0)
    sprint_speed_scale: float = 1000.0
    sprint_speed_decimals: int = 3

    jump_v0_milli_min: int = int(SessionSettings.JUMP_V0_MIN * 1000.0)
    jump_v0_milli_max: int = int(SessionSettings.JUMP_V0_MAX * 1000.0)
    jump_v0_scale: float = 1000.0
    jump_v0_decimals: int = 3

    auto_jump_cooldown_milli_min: int = int(SessionSettings.AUTO_JUMP_COOLDOWN_MIN * 1000.0)
    auto_jump_cooldown_milli_max: int = int(SessionSettings.AUTO_JUMP_COOLDOWN_MAX * 1000.0)
    auto_jump_cooldown_scale: float = 1000.0
    auto_jump_cooldown_decimals: int = 3

DEFAULT_PAUSE_OVERLAY_PARAMS = PauseOverlayParams()