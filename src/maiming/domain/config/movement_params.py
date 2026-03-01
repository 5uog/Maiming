# FILE: src/maiming/domain/config/movement_params.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class MovementParams:
    """
    This parameter set models Bedrock-style player locomotion in a way that is explicitly
    tied to the 20 ticks-per-second reference rate while remaining stable under arbitrary
    simulation sub-stepping. The implementation treats speeds as world-units per second
    and expresses response rates as continuous-time coefficients so that dt partitioning
    does not change steady-state outcomes.
    """
    tick_hz: float = 20.0

    walk_speed: float = 4.317
    sprint_speed: float = 5.612

    crouch_mult: float = 0.3

    gravity: float = 32.0
    fall_speed_max: float = 78.4

    jump_v0: float = 8.4

    accel_ground: float = 30.0
    accel_air: float = 6.0

    sprint_jump_boost: float = 5.0

    auto_jump_probe: float = 0.35
    auto_jump_success_dy: float = 0.90
    auto_jump_cooldown_s: float = 0.12

DEFAULT_MOVEMENT_PARAMS = MovementParams()