# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from ...opengl.runtime.cloud_flow_direction import CLOUD_FLOW_DIRECTIONS, DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction

_LABELS: dict[str, str] = {"east_to_west": "East -> West", "west_to_east": "West -> East", "south_to_north": "South -> North", "north_to_south": "North -> South"}

CLOUD_FLOW_OPTIONS: tuple[tuple[str, str], ...] = tuple((value, _LABELS.get(str(value), str(value).replace("_", " ").title())) for value in CLOUD_FLOW_DIRECTIONS)

def cloud_flow_index_for_value(value: str) -> int:
    normalized = normalize_cloud_flow_direction(str(value))
    for index, (entry, _label) in enumerate(CLOUD_FLOW_OPTIONS):
        if normalized == str(entry):
            return index
    for index, (entry, _label) in enumerate(CLOUD_FLOW_OPTIONS):
        if str(entry) == str(DEFAULT_CLOUD_FLOW_DIRECTION):
            return index
    return 0