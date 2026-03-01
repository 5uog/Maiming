# FILE: src/maiming/application/session/session_settings.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from maiming.domain.config.movement_params import MovementParams, DEFAULT_MOVEMENT_PARAMS
from maiming.domain.config.collision_params import CollisionParams, DEFAULT_COLLISION_PARAMS

@dataclass
class SessionSettings:
    seed: int = 0
    fov_deg: float = 80.0
    mouse_sens_deg_per_px: float = 0.09

    spawn_x: float = 0.0
    spawn_y: float = 1.0
    spawn_z: float = -10.0

    movement: MovementParams = field(default_factory=lambda: DEFAULT_MOVEMENT_PARAMS)
    collision: CollisionParams = field(default_factory=lambda: DEFAULT_COLLISION_PARAMS)

    FOV_MIN: ClassVar[float] = 50.0
    FOV_MAX: ClassVar[float] = 110.0
    SENS_MIN: ClassVar[float] = 0.01
    SENS_MAX: ClassVar[float] = 0.30

    def set_fov(self, fov: float) -> None:
        self.fov_deg = float(max(self.FOV_MIN, min(self.FOV_MAX, float(fov))))

    def set_mouse_sens(self, sens: float) -> None:
        self.mouse_sens_deg_per_px = float(max(self.SENS_MIN, min(self.SENS_MAX, float(sens))))