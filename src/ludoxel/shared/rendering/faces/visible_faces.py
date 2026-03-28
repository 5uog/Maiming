# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ...blocks.models.api import render_boxes_for_block
from ...blocks.models.common import LocalBox
from ...blocks.state.state_codec import parse_state
from ...math.voxel.voxel_faces import face_neighbor_offset
from .face_axes import face_touches_cell_boundary
from .face_occlusion import is_block_face_occluded, is_local_face_occluded
from ..render_types import DefLookup, GetState


@dataclass(frozen=True)
class VisibleFace:
    """I define this record as the tuple (box, face_idx, mn, mx) describing one world-space face that survives every local and neighbor occlusion test. I use it as the canonical intermediate between model visibility analysis and later payload packing."""
    box: LocalBox
    face_idx: int
    mn: tuple[float, float, float]
    mx: tuple[float, float, float]


def _neighbor_is_full_cube_solid(*, x: int, y: int, z: int, face_idx: int, get_state: GetState, def_lookup: DefLookup) -> bool:
    """I define F(face) as the predicate that the neighboring voxel in the face-normal direction resolves to a solid full cube. I use this fast path because such a neighbor guarantees complete occlusion of the contacting face without any finer geometry inspection."""
    dx, dy, dz = face_neighbor_offset(int(face_idx))
    nx = int(x) + int(dx)
    ny = int(y) + int(dy)
    nz = int(z) + int(dz)

    nst = get_state(int(nx), int(ny), int(nz))
    if nst is None:
        return False

    nb, _np = parse_state(str(nst))
    nd = def_lookup(str(nb))
    if nd is None:
        return False

    return bool(nd.is_full_cube) and bool(nd.is_solid)


def _boundary_neighbor_is_full_cube_solid(*, x: int, y: int, z: int, face_idx: int, box: LocalBox, get_state: GetState, def_lookup: DefLookup) -> bool:
    """I define B(face, box) as the full-cube-solid neighbor predicate additionally gated by the condition that the local face actually reaches the voxel boundary. I use this refinement to avoid asking neighboring cells about faces that are interior to a multi-box model."""
    if not face_touches_cell_boundary(int(face_idx), box):
        return False

    return _neighbor_is_full_cube_solid(x=int(x), y=int(y), z=int(z), face_idx=int(face_idx), get_state=get_state, def_lookup=def_lookup)


def iter_visible_faces(*, x: int, y: int, z: int, state_str: str, get_state: GetState, def_lookup: DefLookup, fast_boundary_full_cube_only: bool = False) -> Iterator[VisibleFace]:
    """I define V(state) as the iterator over all faces of the block model that remain after local-face suppression and either the boundary-only or full neighbor-occlusion regime. I use this generator as the single authoritative face-visibility walk for chunk payload synthesis and every other face-level renderer input builder."""
    base, _props = parse_state(str(state_str))
    defn = def_lookup(str(base))
    boxes = list(render_boxes_for_block(str(state_str), get_state, def_lookup, int(x), int(y), int(z)))

    if not boxes:
        return

    full_cube_fast_path = bool(defn is not None and bool(defn.is_full_cube) and bool(defn.is_solid))

    for box in boxes:
        mn = (float(x) + float(box.mn_x), float(y) + float(box.mn_y), float(z) + float(box.mn_z))
        mx = (float(x) + float(box.mx_x), float(y) + float(box.mx_y), float(z) + float(box.mx_z))

        for fi in range(6):
            if is_local_face_occluded(box=box, face_idx=int(fi), boxes=boxes):
                continue

            if bool(fast_boundary_full_cube_only):
                if _boundary_neighbor_is_full_cube_solid(x=int(x), y=int(y), z=int(z), face_idx=int(fi), box=box, get_state=get_state, def_lookup=def_lookup):
                    continue
            else:
                if full_cube_fast_path and _neighbor_is_full_cube_solid(x=int(x), y=int(y), z=int(z), face_idx=int(fi), get_state=get_state, def_lookup=def_lookup):
                    continue

                if is_block_face_occluded(x=int(x), y=int(y), z=int(z), box=box, face_idx=int(fi), get_state=get_state, def_lookup=def_lookup):
                    continue

            yield VisibleFace(box=box, face_idx=int(fi), mn=mn, mx=mx)
