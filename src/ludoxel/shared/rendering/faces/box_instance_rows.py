# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ...blocks.models.common import LocalBox
from .face_row_utils import model_matrix_for_local_box


def cube_rows_from_boxes(boxes: Sequence[LocalBox], parent_transform: np.ndarray) -> np.ndarray:
    """I define R_j = vec(M_parent * T(c_j) * S(s_j)) for each local box j, and I stack these 16-component rows into a contiguous matrix in R^(n x 16). I use this compact representation for shadow casters and every other pipeline that needs box transforms but not per-face UV payloads."""
    if not boxes:
        return np.zeros((0, 16), dtype=np.float32)

    rows = []
    for box in boxes:
        rows.append(np.asarray(model_matrix_for_local_box(parent_transform, box), dtype=np.float32).reshape(16))
    return np.ascontiguousarray(np.vstack(rows), dtype=np.float32)
