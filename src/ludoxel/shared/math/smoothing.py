# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import math

def exp_alpha(rate: float, dt: float) -> float:
    r = float(max(0.0, rate))
    t = float(max(0.0, dt))

    if r <= 1e-9 or t <= 1e-9:
        return 0.0

    return 1.0 - math.exp(-r * t)