# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

FACE_COUNT = 6
BucketCounts = tuple[int, int, int, int, int, int]


def normalize_bucket_counts(bucket_counts: Sequence[int]) -> BucketCounts:
    """I define N(c)_i = max(0, int(c_i)) for i < 6, padding missing entries with zero and truncating surplus entries beyond the six voxel faces. I use this normalization to keep every face-bucket consumer total over loose sequence inputs while preserving the fixed face ordering contract."""
    vals = tuple(int(max(0, int(v))) for v in tuple(bucket_counts)[:FACE_COUNT])
    if len(vals) < FACE_COUNT:
        vals = vals + (0,) * (FACE_COUNT - len(vals))
    return (int(vals[0]), int(vals[1]), int(vals[2]), int(vals[3]), int(vals[4]), int(vals[5]))


def bucket_offsets(bucket_counts: Sequence[int]) -> BucketCounts:
    """I define O_i = sum_{k < i} N(c)_k under the normalized six-face count vector N(c). I use this prefix-sum layout when one flat payload must be indexed by face-local contiguous ranges."""
    c0, c1, c2, c3, c4, _c5 = normalize_bucket_counts(bucket_counts)
    return (0, int(c0), int(c0 + c1), int(c0 + c1 + c2), int(c0 + c1 + c2 + c3), int(c0 + c1 + c2 + c3 + c4))


def empty_face_bucket_arrays(row_width: int, *, dtype: object = np.float32) -> list[np.ndarray]:
    """I define E_i = 0_(0 x w) for each face bucket i in {0,...,5}, where w = max(0, int(row_width)). I use this constructor to give all empty bucket families one canonical shape and dtype policy."""
    width = int(max(0, int(row_width)))
    return [np.zeros((0, width), dtype=dtype) for _ in range(FACE_COUNT)]
