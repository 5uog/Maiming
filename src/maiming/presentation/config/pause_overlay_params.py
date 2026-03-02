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

DEFAULT_PAUSE_OVERLAY_PARAMS = PauseOverlayParams()