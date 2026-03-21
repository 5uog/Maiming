# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import ClassVar

from ....shared.world.config.collision_params import DEFAULT_COLLISION_PARAMS, CollisionParams
from ....shared.world.config.movement_params import DEFAULT_MOVEMENT_PARAMS, MovementParams

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

    FLY_SPEED_MIN: ClassVar[float] = 0.10
    FLY_SPEED_MAX: ClassVar[float] = 32.0

    FLY_ASCEND_SPEED_MIN: ClassVar[float] = 0.10
    FLY_ASCEND_SPEED_MAX: ClassVar[float] = 32.0

    FLY_DESCEND_SPEED_MIN: ClassVar[float] = 0.10
    FLY_DESCEND_SPEED_MAX: ClassVar[float] = 32.0

    def set_fov(self, fov: float) -> None:
        self.fov_deg = float(max(self.FOV_MIN, min(self.FOV_MAX, float(fov))))

    def set_mouse_sens(self, sens: float) -> None:
        self.mouse_sens_deg_per_px = float(max(self.SENS_MIN, min(self.SENS_MAX, float(sens))))

    def set_gravity(self, gravity: float) -> None:
        value = float(max(self.GRAVITY_MIN, min(self.GRAVITY_MAX, float(gravity))))
        self.movement = replace(self.movement, gravity=value)

    def set_walk_speed(self, walk_speed: float) -> None:
        value = float(max(self.WALK_SPEED_MIN, min(self.WALK_SPEED_MAX, float(walk_speed))))
        self.movement = replace(self.movement, walk_speed=value)

    def set_sprint_speed(self, sprint_speed: float) -> None:
        value = float(max(self.SPRINT_SPEED_MIN, min(self.SPRINT_SPEED_MAX, float(sprint_speed))))
        self.movement = replace(self.movement, sprint_speed=value)

    def set_jump_v0(self, jump_v0: float) -> None:
        value = float(max(self.JUMP_V0_MIN, min(self.JUMP_V0_MAX, float(jump_v0))))
        self.movement = replace(self.movement, jump_v0=value)

    def set_auto_jump_cooldown_s(self, cooldown_s: float) -> None:
        value = float(max(self.AUTO_JUMP_COOLDOWN_MIN, min(self.AUTO_JUMP_COOLDOWN_MAX, float(cooldown_s))))
        self.movement = replace(self.movement, auto_jump_cooldown_s=value)

    def set_fly_speed(self, fly_speed: float) -> None:
        value = float(max(self.FLY_SPEED_MIN, min(self.FLY_SPEED_MAX, float(fly_speed))))
        self.movement = replace(self.movement, fly_speed=value)

    def set_fly_ascend_speed(self, fly_ascend_speed: float) -> None:
        value = float(max(self.FLY_ASCEND_SPEED_MIN, min(self.FLY_ASCEND_SPEED_MAX, float(fly_ascend_speed))))
        self.movement = replace(self.movement, fly_ascend_speed=value)

    def set_fly_descend_speed(self, fly_descend_speed: float) -> None:
        value = float(max(self.FLY_DESCEND_SPEED_MIN, min(self.FLY_DESCEND_SPEED_MAX, float(fly_descend_speed))))
        self.movement = replace(self.movement, fly_descend_speed=value)

    def reset_advanced_movement_defaults(self) -> None:
        self.movement = replace(self.movement, gravity=float(DEFAULT_MOVEMENT_PARAMS.gravity), walk_speed=float(DEFAULT_MOVEMENT_PARAMS.walk_speed), sprint_speed=float(DEFAULT_MOVEMENT_PARAMS.sprint_speed), jump_v0=float(DEFAULT_MOVEMENT_PARAMS.jump_v0), auto_jump_cooldown_s=float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s), fly_speed=float(DEFAULT_MOVEMENT_PARAMS.fly_speed), fly_ascend_speed=float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed), fly_descend_speed=float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed))