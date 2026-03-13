# FILE: src/maiming/infrastructure/rendering/opengl/_internal/scene/world_face_source_builder.py
from __future__ import annotations
from typing import Callable, Iterable

import numpy as np

from ......domain.blocks.block_definition import BlockDefinition
from ......domain.blocks.models.common import LocalBox
from ......domain.blocks.state_codec import parse_state
from ..face_bucket_layout import FACE_COUNT, BucketCounts, empty_face_bucket_arrays, normalize_bucket_counts
from ..gl.array_view import as_float32_rows
from .visible_faces import iter_visible_faces

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
    return (_lerp(uA0, uA1, uu0), _lerp(vA0, vA1, vv0), _lerp(uA0, uA1, uu1), _lerp(vA0, vA1, vv1))

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

def empty_face_buckets() -> list[np.ndarray]:
    return empty_face_bucket_arrays(12)

def split_face_sources_to_buckets(face_sources: np.ndarray, bucket_counts: BucketCounts) -> list[np.ndarray]:
    counts = normalize_bucket_counts(bucket_counts)
    out = [np.zeros((int(c), 12), dtype=np.float32) for c in counts]

    if face_sources.size <= 0:
        return out

    src = as_float32_rows(face_sources, cols=14, label="face_sources")

    for row in src:
        fi = int(round(float(row[12])))
        slot = int(round(float(row[13])))

        if fi < 0 or fi >= FACE_COUNT:
            continue
        if slot < 0 or slot >= int(counts[fi]):
            continue

        out[fi][slot, :] = row[:12]

    return out

def build_chunk_face_sources(*, blocks: Iterable[tuple[int, int, int, str]], get_state: GetState, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, BucketCounts]:
    rows: list[list[float]] = []
    bucket_counts = [0 for _ in range(FACE_COUNT)]

    for (x, y, z, state_str) in blocks:
        x = int(x)
        y = int(y)
        z = int(z)

        base, _p = parse_state(str(state_str))
        defn = def_lookup(str(base))

        for face in iter_visible_faces(x=int(x), y=int(y), z=int(z), state_str=str(state_str), get_state=get_state, def_lookup=def_lookup, fast_boundary_full_cube_only=True):
            fi = int(face.face_idx)
            if fi < 0 or fi >= FACE_COUNT:
                continue

            slot = int(bucket_counts[fi])
            bucket_counts[fi] += 1

            mnx, mny, mnz = face.mn
            mxx, mxy, mxz = face.mx

            atlas = uv_lookup(str(state_str), int(fi))

            uv_hint = str(getattr(face.box, "uv_hint", ""))
            if defn is not None and str(defn.kind) == "fence_gate" and uv_hint:
                u0, v0, u1, v1 = _fence_gate_uv_rect(atlas, int(fi), face.box)
            else:
                u0, v0, u1, v1 = _sub_uv_rect(atlas, int(fi), face.box)

            rows.append([float(mnx), float(mny), float(mnz), float(mxx), float(mxy), float(mxz), float(u0), float(v0), float(u1), float(v1), 1.0, 0.0, float(fi), float(slot)])

    counts = normalize_bucket_counts(bucket_counts)

    if not rows:
        return np.zeros((0, 14), dtype=np.float32), counts

    return np.asarray(rows, dtype=np.float32), counts