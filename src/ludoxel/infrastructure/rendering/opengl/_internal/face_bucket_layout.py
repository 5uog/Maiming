# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/face_bucket_layout.py
from __future__ import annotations
from typing import Sequence

import numpy as np

FACE_COUNT = 6
BucketCounts = tuple[int, int, int, int, int, int]


def normalize_bucket_counts(bucket_counts: Sequence[int]) -> BucketCounts:
    vals = tuple(int(max(0, int(v))) for v in tuple(bucket_counts)[:FACE_COUNT])
    if len(vals) < FACE_COUNT:
        vals = vals + (0,) * (FACE_COUNT - len(vals))
    return (int(vals[0]), int(vals[1]), int(vals[2]), int(vals[3]), int(vals[4]), int(vals[5]))


def bucket_offsets(bucket_counts: Sequence[int]) -> BucketCounts:
    c0, c1, c2, c3, c4, _c5 = normalize_bucket_counts(bucket_counts)
    return (
        0,
        int(c0),
        int(c0 + c1),
        int(c0 + c1 + c2),
        int(c0 + c1 + c2 + c3),
        int(c0 + c1 + c2 + c3 + c4),
    )


def empty_face_bucket_arrays(row_width: int, *, dtype: object=np.float32) -> list[np.ndarray]:
    width = int(max(0, int(row_width)))
    return [np.zeros((0, width), dtype=dtype) for _ in range(FACE_COUNT)]
