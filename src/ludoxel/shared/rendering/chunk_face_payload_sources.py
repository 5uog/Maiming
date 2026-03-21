# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np

from ..blocks.block_definition import BlockDefinition
from ..blocks.state.state_codec import parse_state
from .face_bucket_layout import FACE_COUNT, BucketCounts, empty_face_bucket_arrays, normalize_bucket_counts
from .uv_rects import UVRect, fence_gate_uv_rect, sub_uv_rect
from .visible_faces import iter_visible_faces

UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]
GetState = Callable[[int, int, int], str | None]

def _as_face_source_rows(face_sources: np.ndarray) -> np.ndarray:
    arr = np.asarray(face_sources, dtype=np.float32)
    if arr.ndim != 2 or int(arr.shape[1]) != 14:
        raise ValueError("face_sources must be a float32 Nx14 array")
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr, dtype=np.float32)
    return arr

def empty_face_buckets() -> list[np.ndarray]:
    return empty_face_bucket_arrays(12)

def split_face_sources_to_buckets(face_sources: np.ndarray, bucket_counts: BucketCounts) -> list[np.ndarray]:
    counts = normalize_bucket_counts(bucket_counts)
    out = [np.zeros((int(c), 12), dtype=np.float32) for c in counts]

    if face_sources.size <= 0:
        return out

    src = _as_face_source_rows(face_sources)

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
                u0, v0, u1, v1 = fence_gate_uv_rect(atlas, int(fi), face.box)
            else:
                u0, v0, u1, v1 = sub_uv_rect(atlas, int(fi), face.box)

            rows.append([float(mnx), float(mny), float(mnz), float(mxx), float(mxy), float(mxz), float(u0), float(v0), float(u1), float(v1), 1.0, 0.0, float(fi), float(slot)])

    counts = normalize_bucket_counts(bucket_counts)

    if not rows:
        return np.zeros((0, 14), dtype=np.float32), counts

    return np.asarray(rows, dtype=np.float32), counts