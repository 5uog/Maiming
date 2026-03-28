# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ..game.types import DEFAULT_OTHELLO_SACRIFICE_LEVEL, normalize_sacrifice_level

POSITION_WEIGHTS: tuple[int, ...] = (120, -20, 20, 5, 5, 20, -20, 120, -20, -40, -5, -5, -5, -5, -40, -20, 20, -5, 15, 3, 3, 15, -5, 20, 5, -5, 3, 3, 3, 3, -5, 5, 5, -5, 3, 3, 3, 3, -5, 5, 20, -5, 15, 3, 3, 15, -5, 20, -20, -40, -5, -5, -5, -5, -40, -20, 120, -20, 20, 5, 5, 20, -20, 120)


def evaluation_weights(sacrifice_level: int) -> tuple[float, float, float, float]:
    normalized = float(normalize_sacrifice_level(sacrifice_level, default=DEFAULT_OTHELLO_SACRIFICE_LEVEL)) / 4.0
    disc_weight = 1.50 - 1.05 * normalized
    mobility_weight = 0.85 + 0.35 * normalized
    corner_weight = 0.95 + 0.15 * normalized
    frontier_weight = 0.90 + 0.40 * normalized
    return (float(disc_weight), float(mobility_weight), float(corner_weight), float(frontier_weight))
