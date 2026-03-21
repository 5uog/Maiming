# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

RENDER_DISTANCE_MIN_CHUNKS = 2
RENDER_DISTANCE_MAX_CHUNKS = 50

def clamp_render_distance_chunks(value: int) -> int:
    return int(max(RENDER_DISTANCE_MIN_CHUNKS, min(RENDER_DISTANCE_MAX_CHUNKS, int(value))))