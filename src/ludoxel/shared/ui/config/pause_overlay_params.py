# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass

from ....application.runtime.state.session_settings import SessionSettings
from ...world.config.render_distance import RENDER_DISTANCE_MAX_CHUNKS, RENDER_DISTANCE_MIN_CHUNKS

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

    render_dist_min: int = int(RENDER_DISTANCE_MIN_CHUNKS)
    render_dist_max: int = int(RENDER_DISTANCE_MAX_CHUNKS)

    bob_strength_percent_min: int = 0
    bob_strength_percent_max: int = 100

    shake_strength_percent_min: int = 0
    shake_strength_percent_max: int = 100

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

    fly_speed_milli_min: int = int(SessionSettings.FLY_SPEED_MIN * 1000.0)
    fly_speed_milli_max: int = int(SessionSettings.FLY_SPEED_MAX * 1000.0)
    fly_speed_scale: float = 1000.0
    fly_speed_decimals: int = 3

    fly_ascend_speed_milli_min: int = int(SessionSettings.FLY_ASCEND_SPEED_MIN * 1000.0)
    fly_ascend_speed_milli_max: int = int(SessionSettings.FLY_ASCEND_SPEED_MAX * 1000.0)
    fly_ascend_speed_scale: float = 1000.0
    fly_ascend_speed_decimals: int = 3

    fly_descend_speed_milli_min: int = int(SessionSettings.FLY_DESCEND_SPEED_MIN * 1000.0)
    fly_descend_speed_milli_max: int = int(SessionSettings.FLY_DESCEND_SPEED_MAX * 1000.0)
    fly_descend_speed_scale: float = 1000.0
    fly_descend_speed_decimals: int = 3

DEFAULT_PAUSE_OVERLAY_PARAMS = PauseOverlayParams()