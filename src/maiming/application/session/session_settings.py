# FILE: src/maiming/application/session/session_settings.py
from __future__ import annotations

from dataclasses import dataclass, field, replace
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

    GRAVITY_MIN: ClassVar[float] = 1.0
    GRAVITY_MAX: ClassVar[float] = 64.0

    WALK_SPEED_MIN: ClassVar[float] = 0.10
    WALK_SPEED_MAX: ClassVar[float] = 12.0

    SPRINT_SPEED_MIN: ClassVar[float] = 0.10
    SPRINT_SPEED_MAX: ClassVar[float] = 16.0

    JUMP_V0_MIN: ClassVar[float] = 0.10
    JUMP_V0_MAX: ClassVar[float] = 20.0

    AUTO_JUMP_COOLDOWN_MIN: ClassVar[float] = 0.0
    AUTO_JUMP_COOLDOWN_MAX: ClassVar[float] = 2.0

    def set_fov(self, fov: float) -> None:
        self.fov_deg = float(max(self.FOV_MIN, min(self.FOV_MAX, float(fov))))

    def set_mouse_sens(self, sens: float) -> None:
        self.mouse_sens_deg_per_px = float(max(self.SENS_MIN, min(self.SENS_MAX, float(sens))))

    def set_gravity(self, gravity: float) -> None:
        v = float(max(self.GRAVITY_MIN, min(self.GRAVITY_MAX, float(gravity))))
        self.movement = replace(self.movement, gravity=v)

    def set_walk_speed(self, walk_speed: float) -> None:
        v = float(max(self.WALK_SPEED_MIN, min(self.WALK_SPEED_MAX, float(walk_speed))))
        self.movement = replace(self.movement, walk_speed=v)

    def set_sprint_speed(self, sprint_speed: float) -> None:
        v = float(max(self.SPRINT_SPEED_MIN, min(self.SPRINT_SPEED_MAX, float(sprint_speed))))
        self.movement = replace(self.movement, sprint_speed=v)

    def set_jump_v0(self, jump_v0: float) -> None:
        v = float(max(self.JUMP_V0_MIN, min(self.JUMP_V0_MAX, float(jump_v0))))
        self.movement = replace(self.movement, jump_v0=v)

    def set_auto_jump_cooldown_s(self, cooldown_s: float) -> None:
        v = float(
            max(
                self.AUTO_JUMP_COOLDOWN_MIN,
                min(self.AUTO_JUMP_COOLDOWN_MAX, float(cooldown_s)),
            )
        )
        self.movement = replace(self.movement, auto_jump_cooldown_s=v)

    def reset_advanced_movement_defaults(self) -> None:
        self.movement = replace(
            self.movement,
            gravity=float(DEFAULT_MOVEMENT_PARAMS.gravity),
            walk_speed=float(DEFAULT_MOVEMENT_PARAMS.walk_speed),
            sprint_speed=float(DEFAULT_MOVEMENT_PARAMS.sprint_speed),
            jump_v0=float(DEFAULT_MOVEMENT_PARAMS.jump_v0),
            auto_jump_cooldown_s=float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s),
        )