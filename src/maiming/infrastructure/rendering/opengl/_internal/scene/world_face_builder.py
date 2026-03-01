# FILE: src/maiming/infrastructure/rendering/opengl/scene/world_face_builder.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from maiming.domain.blocks.state_codec import parse_state
from maiming.domain.blocks.models.api import render_boxes_for_block, LocalBox
from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.core.math.vec3 import Vec3

from .instance_types import BlockFaceInstanceGPU, ShadowCasterGPU

UVRect = tuple[float, float, float, float]
UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]

def _overlap_1d(a0: float, a1: float, b0: float, b1: float) -> bool:
    return (float(a1) > float(b0)) and (float(b1) > float(a0))

def _internal_face_mask(boxes: list[LocalBox]) -> set[tuple[int, int]]:
    eps = 1e-7
    internal: set[tuple[int, int]] = set()

    def eq(a: float, b: float) -> bool:
        return abs(float(a) - float(b)) <= eps

    for i, a in enumerate(boxes):
        for j, b in enumerate(boxes):
            if i == j:
                continue

            if eq(a.mx_x, b.mn_x):
                if eq(a.mn_y, b.mn_y) and eq(a.mx_y, b.mx_y) and eq(a.mn_z, b.mn_z) and eq(a.mx_z, b.mx_z):
                    internal.add((i, 0))
                    internal.add((j, 1))

            if eq(a.mn_x, b.mx_x):
                if eq(a.mn_y, b.mn_y) and eq(a.mx_y, b.mx_y) and eq(a.mn_z, b.mn_z) and eq(a.mx_z, b.mx_z):
                    internal.add((i, 1))
                    internal.add((j, 0))

            if eq(a.mx_y, b.mn_y):
                if eq(a.mn_x, b.mn_x) and eq(a.mx_x, b.mx_x) and eq(a.mn_z, b.mn_z) and eq(a.mx_z, b.mx_z):
                    internal.add((i, 2))
                    internal.add((j, 3))

            if eq(a.mn_y, b.mx_y):
                if eq(a.mn_x, b.mn_x) and eq(a.mx_x, b.mx_x) and eq(a.mn_z, b.mn_z) and eq(a.mx_z, b.mx_z):
                    internal.add((i, 3))
                    internal.add((j, 2))

            if eq(a.mx_z, b.mn_z):
                if eq(a.mn_x, b.mn_x) and eq(a.mx_x, b.mx_x) and eq(a.mn_y, b.mn_y) and eq(a.mx_y, b.mx_y):
                    internal.add((i, 4))
                    internal.add((j, 5))

            if eq(a.mn_z, b.mx_z):
                if eq(a.mn_x, b.mn_x) and eq(a.mx_x, b.mx_x) and eq(a.mn_y, b.mn_y) and eq(a.mx_y, b.mx_y):
                    internal.add((i, 5))
                    internal.add((j, 4))

    return internal

def _sub_uv_rect(atlas: UVRect, face_idx: int, b: LocalBox) -> UVRect:
    uA0, vA0, uA1, vA1 = atlas

    def lerp(a: float, b: float, t: float) -> float:
        return float(a) + (float(b) - float(a)) * float(t)

    def clamp01(x: float) -> float:
        v = float(x)
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    fi = int(face_idx)

    if fi == 0:
        u0, u1 = float(b.mn_z), float(b.mx_z)
        v0, v1 = float(b.mn_y), float(b.mx_y)
    elif fi == 1:
        u0, u1 = float(b.mx_z), float(b.mn_z)
        v0, v1 = float(b.mn_y), float(b.mx_y)
    elif fi == 2:
        u0, u1 = float(b.mn_x), float(b.mx_x)
        v0, v1 = float(b.mn_z), float(b.mx_z)
    elif fi == 3:
        u0, u1 = float(b.mn_x), float(b.mx_x)
        v0, v1 = float(b.mx_z), float(b.mn_z)
    elif fi == 4:
        u0, u1 = float(b.mx_x), float(b.mn_x)
        v0, v1 = float(b.mn_y), float(b.mx_y)
    else:
        u0, u1 = float(b.mn_x), float(b.mx_x)
        v0, v1 = float(b.mn_y), float(b.mx_y)

    u0 = clamp01(u0)
    u1 = clamp01(u1)
    v0 = clamp01(v0)
    v1 = clamp01(v1)

    return (
        lerp(uA0, uA1, u0),
        lerp(vA0, vA1, v0),
        lerp(uA0, uA1, u1),
        lerp(vA0, vA1, v1),
    )


def build_world_faces(
    blocks: Iterable[tuple[int, int, int, str]],
    uv_lookup: UVLookup,
    def_lookup: DefLookup,
    sun_dir: Vec3,
    shadow_dark_mul: float,
) -> tuple[list[list[BlockFaceInstanceGPU]], list[ShadowCasterGPU]]:
    b_list = list(blocks)

    state_at: dict[tuple[int, int, int], str] = {}
    for (x, y, z, bid) in b_list:
        state_at[(int(x), int(y), int(z))] = str(bid)

    def get_state(x: int, y: int, z: int) -> str | None:
        return state_at.get((int(x), int(y), int(z)))

    faces: list[list[BlockFaceInstanceGPU]] = [[], [], [], [], [], []]
    casters: list[ShadowCasterGPU] = []

    for (x, y, z, state_str) in b_list:
        x = int(x)
        y = int(y)
        z = int(z)

        base, _p = parse_state(str(state_str))
        defn = def_lookup(str(base))

        boxes = render_boxes_for_block(str(state_str), get_state, def_lookup, x, y, z)
        if not boxes:
            continue

        internal = _internal_face_mask(boxes)

        for bi, b in enumerate(boxes):
            mnx = float(x) + float(b.mn_x)
            mny = float(y) + float(b.mn_y)
            mnz = float(z) + float(b.mn_z)
            mxx = float(x) + float(b.mx_x)
            mxy = float(y) + float(b.mx_y)
            mxz = float(z) + float(b.mx_z)

            cx = (mnx + mxx) * 0.5
            cy = (mny + mxy) * 0.5
            cz = (mnz + mxz) * 0.5
            sx = max(0.0, float(mxx - mnx))
            sy = max(0.0, float(mxy - mny))
            sz = max(0.0, float(mxz - mnz))
            casters.append(ShadowCasterGPU(cx, cy, cz, sx, sy, sz))

            for fi in range(6):
                if (bi, fi) in internal:
                    continue

                if defn is not None and bool(defn.is_full_cube) and bool(defn.is_solid):
                    nx, ny, nz = x, y, z
                    if fi == 0:
                        nx += 1
                    elif fi == 1:
                        nx -= 1
                    elif fi == 2:
                        ny += 1
                    elif fi == 3:
                        ny -= 1
                    elif fi == 4:
                        nz += 1
                    else:
                        nz -= 1

                    nst = get_state(nx, ny, nz)
                    if nst is not None:
                        nb, _np = parse_state(nst)
                        nd = def_lookup(str(nb))
                        if nd is None or (bool(nd.is_full_cube) and bool(nd.is_solid)):
                            continue

                atlas = uv_lookup(str(state_str), int(fi))
                u0, v0, u1, v1 = _sub_uv_rect(atlas, int(fi), b)

                faces[fi].append(
                    BlockFaceInstanceGPU(
                        mn_x=mnx, mn_y=mny, mn_z=mnz,
                        mx_x=mxx, mx_y=mxy, mx_z=mxz,
                        u0=float(u0), v0=float(v0), u1=float(u1), v1=float(v1),
                        shade=1.0,
                        uv_rot=0.0,
                    )
                )

    return faces, casters