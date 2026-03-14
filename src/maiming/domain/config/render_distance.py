# FILE: src/maiming/domain/config/render_distance.py
from __future__ import annotations

RENDER_DISTANCE_MIN_CHUNKS = 2
RENDER_DISTANCE_MAX_CHUNKS = 50

def clamp_render_distance_chunks(value: int) -> int:
    return int(max(RENDER_DISTANCE_MIN_CHUNKS, min(RENDER_DISTANCE_MAX_CHUNKS, int(value))))