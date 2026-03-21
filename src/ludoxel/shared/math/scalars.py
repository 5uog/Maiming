# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

def clampf(x: float, lo: float, hi: float) -> float:
    value = float(x)
    low = float(lo)
    high = float(hi)
    if value < low:
        return low
    if value > high:
        return high
    return value