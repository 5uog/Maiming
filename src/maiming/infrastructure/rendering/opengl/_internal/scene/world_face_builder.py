# FILE: src/maiming/infrastructure/rendering/opengl/_internal/scene/world_face_builder.py
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.domain.blocks.models.common import LocalBox
from maiming.domain.blocks.state_codec import parse_state
from maiming.infrastructure.rendering.opengl._internal.scene.visible_faces import iter_visible_faces

UVRect = tuple[float, float, float, float]
UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]
GetState = Callable[[int, int, int], str | None]

def _lerp(a: float, c: float, t: float) -> float:
    return float(a) + (float(c) - float(a)) * float(t)

def _clamp01(x: float) -> float:
    v = float(x)
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v

def _uv_rect(atlas: UVRect, u0: float, v0: float, u1: float, v1: float) -> UVRect:
    uA0, vA0, uA1, vA1 = atlas
    uu0 = _clamp01(u0)
    vv0 = _clamp01(v0)
    uu1 = _clamp01(u1)
    vv1 = _clamp01(v1)
    return (
        _lerp(uA0, uA1, uu0),
        _lerp(vA0, vA1, vv0),
        _lerp(uA0, uA1, uu1),
        _lerp(vA0, vA1, vv1),
    )

def _sub_uv_rect(atlas: UVRect, face_idx: int, b: LocalBox) -> UVRect:
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

    return _uv_rect(atlas, u0, v0, u1, v1)

def _fence_gate_uv_rect(atlas: UVRect, face_idx: int, b: LocalBox) -> UVRect:
    fi = int(face_idx)

    if fi == 0 or fi == 1:
        u0, u1 = float(b.mn_z), float(b.mx_z)
        v0, v1 = float(b.mn_y), float(b.mx_y)
    elif fi == 2 or fi == 3:
        u0, u1 = float(b.mn_x), float(b.mx_x)
        v0, v1 = float(b.mn_z), float(b.mx_z)
    else:
        u0, u1 = float(b.mn_x), float(b.mx_x)
        v0, v1 = float(b.mn_y), float(b.mx_y)

    return _uv_rect(atlas, u0, v0, u1, v1)

def build_chunk_mesh(
    *,
    blocks: Iterable[tuple[int, int, int, str]],
    get_state: GetState,
    uv_lookup: UVLookup,
    def_lookup: DefLookup,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    faces_rows: list[list[list[float]]] = [[], [], [], [], [], []]

    for (x, y, z, state_str) in blocks:
        x = int(x)
        y = int(y)
        z = int(z)

        base, _p = parse_state(str(state_str))
        defn = def_lookup(str(base))

        for face in iter_visible_faces(
            x=int(x),
            y=int(y),
            z=int(z),
            state_str=str(state_str),
            get_state=get_state,
            def_lookup=def_lookup,
        ):
            mnx, mny, mnz = face.mn
            mxx, mxy, mxz = face.mx

            atlas = uv_lookup(str(state_str), int(face.face_idx))

            if defn is not None and str(defn.kind) == "fence_gate" and str(face.box.uv_hint):
                u0, v0, u1, v1 = _fence_gate_uv_rect(atlas, int(face.face_idx), face.box)
            else:
                u0, v0, u1, v1 = _sub_uv_rect(atlas, int(face.face_idx), face.box)

            faces_rows[int(face.face_idx)].append(
                [
                    mnx, mny, mnz,
                    mxx, mxy, mxz,
                    float(u0), float(v0), float(u1), float(v1),
                    1.0,
                    0.0,
                ]
            )

    faces_np: list[np.ndarray] = []
    for rows in faces_rows:
        if not rows:
            faces_np.append(np.zeros((0, 12), dtype=np.float32))
        else:
            faces_np.append(np.asarray(rows, dtype=np.float32))

    shadow_faces_np = list(faces_np)
    return faces_np, shadow_faces_np