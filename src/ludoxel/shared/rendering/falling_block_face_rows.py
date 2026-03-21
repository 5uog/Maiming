# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Callable

import numpy as np

from ...application.runtime.state.render_snapshot import FallingBlockRenderSampleDTO
from ..blocks.block_definition import BlockDefinition
from ..blocks.models.api import render_boxes_for_block
from ..blocks.models.common import LocalBox
from ..blocks.state.state_codec import parse_state
from ..math.transform_matrices import compose_matrices, scale_matrix, translate_matrix
from .face_occlusion import is_local_face_occluded
from .uv_rects import UVRect, fence_gate_uv_rect, sub_uv_rect

UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]

def _empty_face_rows() -> tuple[np.ndarray, ...]:
    return tuple(np.zeros((0, 20), dtype=np.float32) for _ in range(6))

def _model_matrix_for_box(*, base_x: float, base_y: float, base_z: float, box: LocalBox) -> np.ndarray:
    center_x = float(base_x) + 0.5 * (float(box.mn_x) + float(box.mx_x))
    center_y = float(base_y) + 0.5 * (float(box.mn_y) + float(box.mx_y))
    center_z = float(base_z) + 0.5 * (float(box.mn_z) + float(box.mx_z))
    size_x = float(box.mx_x) - float(box.mn_x)
    size_y = float(box.mx_y) - float(box.mn_y)
    size_z = float(box.mx_z) - float(box.mn_z)
    return compose_matrices(translate_matrix(float(center_x), float(center_y), float(center_z)), scale_matrix(float(size_x), float(size_y), float(size_z)))

def build_falling_block_face_rows(*, samples: tuple[FallingBlockRenderSampleDTO, ...], uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, ...]:
    if not samples:
        return _empty_face_rows()

    buffers: list[list[list[float]]] = [[] for _ in range(6)]
    get_state = lambda _x, _y, _z: None

    for sample in samples:
        state_str = str(sample.state_str)
        base_id, _props = parse_state(str(state_str))
        defn = def_lookup(str(base_id))
        boxes = list(render_boxes_for_block(str(state_str), get_state, def_lookup, 0, 0, 0))
        if not boxes:
            continue

        for box in boxes:
            model = np.asarray(_model_matrix_for_box(base_x=float(sample.x), base_y=float(sample.y), base_z=float(sample.z), box=box), dtype=np.float32).reshape(16)
            for face_idx in range(6):
                if is_local_face_occluded(box=box, face_idx=int(face_idx), boxes=boxes):
                    continue

                atlas = uv_lookup(str(state_str), int(face_idx))
                uv_hint = str(getattr(box, "uv_hint", ""))
                if defn is not None and str(defn.kind) == "fence_gate" and uv_hint:
                    uv_rect = fence_gate_uv_rect(atlas, int(face_idx), box)
                else:
                    uv_rect = sub_uv_rect(atlas, int(face_idx), box)

                row = list(model)
                row.extend([float(uv_rect[0]), float(uv_rect[1]), float(uv_rect[2]), float(uv_rect[3])])
                buffers[int(face_idx)].append(row)

    return tuple(np.asarray(rows, dtype=np.float32) if rows else np.zeros((0, 20), dtype=np.float32) for rows in buffers)