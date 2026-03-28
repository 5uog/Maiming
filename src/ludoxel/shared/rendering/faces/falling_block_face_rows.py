# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from ..render_snapshot import FallingBlockRenderSampleDTO
from ...blocks.models.api import render_boxes_for_block
from ...blocks.state.state_codec import parse_state
from ...math.transform_matrices import translate_matrix
from .face_occlusion import is_local_face_occluded
from .face_row_utils import append_face_instance, atlas_face_uv, empty_textured_face_rows, face_rows_from_buffers, model_matrix_for_local_box
from ..render_types import DefLookup, UVLookup


def build_falling_block_face_rows(*, samples: tuple[FallingBlockRenderSampleDTO, ...], uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, ...]:
    """I define F_i as the aggregate instanced-face payload for all transient falling-block samples over face index i. For each sample I materialize the render boxes of its encoded block state at the sample translation, eliminate locally occluded faces, and append vec(M_box, U_face) rows into the six face buckets."""
    if not samples:
        return empty_textured_face_rows()

    buffers: list[list[list[float]]] = [[] for _ in range(6)]
    get_state = lambda _x, _y, _z: None

    for sample in samples:
        state_str = str(sample.state_str)
        base_id, _props = parse_state(str(state_str))
        defn = def_lookup(str(base_id))
        boxes = list(render_boxes_for_block(str(state_str), get_state, def_lookup, 0, 0, 0))
        if not boxes:
            continue
        parent_transform = translate_matrix(float(sample.x), float(sample.y), float(sample.z))
        kind = None if defn is None else str(defn.kind)

        for box in boxes:
            model = model_matrix_for_local_box(parent_transform, box)
            for face_idx in range(6):
                if is_local_face_occluded(box=box, face_idx=int(face_idx), boxes=boxes):
                    continue

                atlas = uv_lookup(str(state_str), int(face_idx))
                uv_rect = atlas_face_uv(atlas, int(face_idx), box, kind=kind)
                append_face_instance(buffers, int(face_idx), model, uv_rect)

    return face_rows_from_buffers(buffers)
