# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/facade/cloud_flow_direction.py
from __future__ import annotations

DEFAULT_CLOUD_FLOW_DIRECTION: str = "west_to_east"
CLOUD_FLOW_DIRECTIONS: tuple[str, str, str, str] = ("east_to_west", DEFAULT_CLOUD_FLOW_DIRECTION, "south_to_north", "north_to_south")


def normalize_cloud_flow_direction(raw: str) -> str:
    s = str(raw).strip().lower()
    if s in CLOUD_FLOW_DIRECTIONS:
        return s
    return DEFAULT_CLOUD_FLOW_DIRECTION
