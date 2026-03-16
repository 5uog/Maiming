# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/scene/face_occlusion.py
from __future__ import annotations

from typing import Callable

from ......core.grid.face_index import face_neighbor_offset
from ......domain.blocks.block_definition import BlockDefinition
from ......domain.blocks.state_codec import parse_state
from ......domain.blocks.models.api import render_boxes_for_block
from ......domain.blocks.models.common import LocalBox
from .face_axes import approx_eq, face_rect, face_touches_cell_boundary

GetState = Callable[[int, int, int], str | None]
DefLookup = Callable[[str], BlockDefinition | None]

_EPS = 1e-7


def _face_boundary_offset(face_idx: int, box: LocalBox) -> tuple[int, int, int] | None:
    if not face_touches_cell_boundary(int(face_idx), box):
        return None
    return face_neighbor_offset(int(face_idx))


def _neighbor_cover_rects(face_idx: int, boxes: list[LocalBox]) -> list[tuple[float, float, float, float]]:
    fi = int(face_idx)
    out: list[tuple[float, float, float, float]] = []

    for b in boxes:
        if fi == 0:
            if approx_eq(float(b.mn_x), 0.0):
                out.append((float(b.mn_y), float(b.mx_y), float(b.mn_z), float(b.mx_z)))
            continue
        if fi == 1:
            if approx_eq(float(b.mx_x), 1.0):
                out.append((float(b.mn_y), float(b.mx_y), float(b.mn_z), float(b.mx_z)))
            continue
        if fi == 2:
            if approx_eq(float(b.mn_y), 0.0):
                out.append((float(b.mn_x), float(b.mx_x), float(b.mn_z), float(b.mx_z)))
            continue
        if fi == 3:
            if approx_eq(float(b.mx_y), 1.0):
                out.append((float(b.mn_x), float(b.mx_x), float(b.mn_z), float(b.mx_z)))
            continue
        if fi == 4:
            if approx_eq(float(b.mn_z), 0.0):
                out.append((float(b.mn_x), float(b.mx_x), float(b.mn_y), float(b.mx_y)))
            continue
        if fi == 5:
            if approx_eq(float(b.mx_z), 1.0):
                out.append((float(b.mn_x), float(b.mx_x), float(b.mn_y), float(b.mx_y)))

    return out


def _local_cover_rects(face_idx: int, box: LocalBox, boxes: list[LocalBox]) -> list[tuple[float, float, float, float]]:
    fi = int(face_idx)
    out: list[tuple[float, float, float, float]] = []

    for other in boxes:
        if other is box:
            continue
        if fi == 0:
            if approx_eq(float(other.mn_x), float(box.mx_x)):
                out.append((float(other.mn_y), float(other.mx_y), float(other.mn_z), float(other.mx_z)))
            continue
        if fi == 1:
            if approx_eq(float(other.mx_x), float(box.mn_x)):
                out.append((float(other.mn_y), float(other.mx_y), float(other.mn_z), float(other.mx_z)))
            continue
        if fi == 2:
            if approx_eq(float(other.mn_y), float(box.mx_y)):
                out.append((float(other.mn_x), float(other.mx_x), float(other.mn_z), float(other.mx_z)))
            continue
        if fi == 3:
            if approx_eq(float(other.mx_y), float(box.mn_y)):
                out.append((float(other.mn_x), float(other.mx_x), float(other.mn_z), float(other.mx_z)))
            continue
        if fi == 4:
            if approx_eq(float(other.mn_z), float(box.mx_z)):
                out.append((float(other.mn_x), float(other.mx_x), float(other.mn_y), float(other.mx_y)))
            continue
        if fi == 5:
            if approx_eq(float(other.mx_z), float(box.mn_z)):
                out.append((float(other.mn_x), float(other.mx_x), float(other.mn_y), float(other.mx_y)))

    return out


def _sorted_unique(values: list[float]) -> list[float]:
    q: dict[int, float] = {}
    for v in values:
        q[int(round(float(v) / _EPS))] = float(v)
    return [q[k] for k in sorted(q.keys())]


def _fully_covered(target_rect: tuple[float, float, float, float], cover_rects: list[tuple[float, float, float, float]]) -> bool:
    tu0, tu1, tv0, tv1 = target_rect

    if (tu1 - tu0) <= _EPS or (tv1 - tv0) <= _EPS:
        return False

    clipped: list[tuple[float, float, float, float]] = []
    us = [float(tu0), float(tu1)]
    vs = [float(tv0), float(tv1)]

    for ru0, ru1, rv0, rv1 in cover_rects:
        cu0 = max(float(tu0), float(ru0))
        cu1 = min(float(tu1), float(ru1))
        cv0 = max(float(tv0), float(rv0))
        cv1 = min(float(tv1), float(rv1))

        if (cu1 - cu0) <= _EPS or (cv1 - cv0) <= _EPS:
            continue

        clipped.append((float(cu0), float(cu1), float(cv0), float(cv1)))
        us.extend((float(cu0), float(cu1)))
        vs.extend((float(cv0), float(cv1)))

    if not clipped:
        return False

    us_s = _sorted_unique(us)
    vs_s = _sorted_unique(vs)

    if len(us_s) < 2 or len(vs_s) < 2:
        return False

    for ui in range(len(us_s) - 1):
        u0 = float(us_s[ui])
        u1 = float(us_s[ui + 1])
        if (u1 - u0) <= _EPS:
            continue

        uc = (u0 + u1) * 0.5

        for vi in range(len(vs_s) - 1):
            v0 = float(vs_s[vi])
            v1 = float(vs_s[vi + 1])
            if (v1 - v0) <= _EPS:
                continue

            vc = (v0 + v1) * 0.5

            if uc < (tu0 - _EPS) or uc > (tu1 + _EPS) or vc < (tv0 - _EPS) or vc > (tv1 + _EPS):
                continue

            covered = False
            for ru0, ru1, rv0, rv1 in clipped:
                if (uc >= (float(ru0) - _EPS) and uc <= (float(ru1) + _EPS) and vc >= (float(rv0) - _EPS) and vc <= (float(rv1) + _EPS)):
                    covered = True
                    break

            if not covered:
                return False

    return True


def is_local_face_occluded(*, box: LocalBox, face_idx: int, boxes: list[LocalBox]) -> bool:
    target = face_rect(int(face_idx), box)
    rects = _local_cover_rects(int(face_idx), box, boxes)
    if not rects:
        return False
    return _fully_covered(target, rects)


def is_block_face_occluded(*, x: int, y: int, z: int, box: LocalBox, face_idx: int, get_state: GetState, def_lookup: DefLookup) -> bool:
    off = _face_boundary_offset(int(face_idx), box)
    if off is None:
        return False

    dx, dy, dz = off
    nx = int(x) + int(dx)
    ny = int(y) + int(dy)
    nz = int(z) + int(dz)

    nst = get_state(int(nx), int(ny), int(nz))
    if nst is None:
        return False

    nb_base, _nb_props = parse_state(str(nst))
    nb_def = def_lookup(str(nb_base))
    if nb_def is None or (not bool(nb_def.is_solid)):
        return False

    nboxes = list(render_boxes_for_block(str(nst), get_state, def_lookup, int(nx), int(ny), int(nz)))
    if not nboxes:
        return False

    target = face_rect(int(face_idx), box)
    rects = _neighbor_cover_rects(int(face_idx), nboxes)
    if not rects:
        return False

    return _fully_covered(target, rects)
