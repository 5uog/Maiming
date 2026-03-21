# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class CollisionParams:
    eps: float = 1e-4
    ground_probe: float = 0.03
    step_height: float = 0.5625
    nearby_xz_pad: int = 1
    nearby_y_down_pad: int = 2
    nearby_y_up_pad: int = 1
    sneak_step: float = 0.05

DEFAULT_COLLISION_PARAMS = CollisionParams()