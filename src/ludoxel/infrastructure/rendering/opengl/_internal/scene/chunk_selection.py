# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/scene/chunk_selection.py
from __future__ import annotations

from collections.abc import Callable, Iterable

import numpy as np

from ......domain.world.chunking import ChunkKey, normalize_chunk_key
from .chunk_visibility import chunk_intersects_clip_volume

ChunkPredicate = Callable[[ChunkKey], bool]


def within_render_distance(chunk_key: ChunkKey, camera_chunk: ChunkKey, render_distance_chunks: int) -> bool:
    ck = normalize_chunk_key(chunk_key)
    cam = normalize_chunk_key(camera_chunk)
    rd = int(render_distance_chunks)

    dx = abs(int(ck[0]) - int(cam[0]))
    dy = abs(int(ck[1]) - int(cam[1]))
    dz = abs(int(ck[2]) - int(cam[2]))
    return (dx <= rd) and (dy <= 1) and (dz <= rd)


def select_visible_chunks(chunk_keys: Iterable[ChunkKey], matrix: np.ndarray, *, predicate: ChunkPredicate | None=None) -> list[ChunkKey]:
    out: list[ChunkKey] = []

    for chunk_key in chunk_keys:
        ck = normalize_chunk_key(chunk_key)

        if predicate is not None and (not bool(predicate(ck))):
            continue

        if not chunk_intersects_clip_volume(ck, matrix):
            continue

        out.append(ck)

    return out
