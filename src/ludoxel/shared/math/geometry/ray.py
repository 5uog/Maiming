# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ..vec3 import Vec3

@dataclass(frozen=True)
class Ray:
    origin: Vec3
    direction: Vec3