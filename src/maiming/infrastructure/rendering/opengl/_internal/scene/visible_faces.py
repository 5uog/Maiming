# FILE: src/maiming/infrastructure/rendering/opengl/_internal/scene/visible_faces.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.domain.blocks.models.api import render_boxes_for_block
from maiming.domain.blocks.models.box_adjacency import internal_face_mask
from maiming.domain.blocks.models.common import LocalBox
from maiming.domain.blocks.state_codec import parse_state
from maiming.infrastructure.rendering.opengl._internal.scene.face_occlusion import is_block_face_occluded

GetState = Callable[[int, int, int], str | None]
DefLookup = Callable[[str], BlockDefinition | None]

@dataclass(frozen=True)
class VisibleFace:
    box: LocalBox
    face_idx: int
    mn: tuple[float, float, float]
    mx: tuple[float, float, float]

def _neighbor_cell(x: int, y: int, z: int, face_idx: int) -> tuple[int, int, int]:
    fi = int(face_idx)

    if fi == 0:
        return (int(x + 1), int(y), int(z))
    if fi == 1:
        return (int(x - 1), int(y), int(z))
    if fi == 2:
        return (int(x), int(y + 1), int(z))
    if fi == 3:
        return (int(x), int(y - 1), int(z))
    if fi == 4:
        return (int(x), int(y), int(z + 1))
    return (int(x), int(y), int(z - 1))

def _neighbor_is_full_cube_solid(
    *,
    x: int,
    y: int,
    z: int,
    face_idx: int,
    get_state: GetState,
    def_lookup: DefLookup,
) -> bool:
    nx, ny, nz = _neighbor_cell(int(x), int(y), int(z), int(face_idx))
    nst = get_state(int(nx), int(ny), int(nz))
    if nst is None:
        return False

    nb, _np = parse_state(str(nst))
    nd = def_lookup(str(nb))
    if nd is None:
        return False

    return bool(nd.is_full_cube) and bool(nd.is_solid)

def iter_visible_faces(
    *,
    x: int,
    y: int,
    z: int,
    state_str: str,
    get_state: GetState,
    def_lookup: DefLookup,
) -> Iterator[VisibleFace]:
    base, _props = parse_state(str(state_str))
    defn = def_lookup(str(base))

    boxes = render_boxes_for_block(
        str(state_str),
        get_state,
        def_lookup,
        int(x),
        int(y),
        int(z),
    )
    if not boxes:
        return

    internal = internal_face_mask(boxes)

    for bi, box in enumerate(boxes):
        mn = (
            float(x) + float(box.mn_x),
            float(y) + float(box.mn_y),
            float(z) + float(box.mn_z),
        )
        mx = (
            float(x) + float(box.mx_x),
            float(y) + float(box.mx_y),
            float(z) + float(box.mx_z),
        )

        for fi in range(6):
            if (bi, fi) in internal:
                continue

            if defn is not None and bool(defn.is_full_cube) and bool(defn.is_solid):
                if _neighbor_is_full_cube_solid(
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    face_idx=int(fi),
                    get_state=get_state,
                    def_lookup=def_lookup,
                ):
                    continue

            if is_block_face_occluded(
                x=int(x),
                y=int(y),
                z=int(z),
                box=box,
                face_idx=int(fi),
                get_state=get_state,
                def_lookup=def_lookup,
            ):
                continue

            yield VisibleFace(
                box=box,
                face_idx=int(fi),
                mn=mn,
                mx=mx,
            )