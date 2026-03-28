# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from ...blocks.state.state_codec import parse_state
from .face_bucket_layout import FACE_COUNT, BucketCounts, empty_face_bucket_arrays, normalize_bucket_counts
from .face_row_utils import atlas_face_uv
from ..render_types import DefLookup, GetState, UVLookup
from .visible_faces import iter_visible_faces


def _as_face_source_rows(face_sources: np.ndarray) -> np.ndarray:
    """I define A = ascontiguousarray(face_sources) under the invariant shape A in R^(N x 14). I enforce this contract because every downstream bucket split assumes the row schema (bounds, UVs, flags, face index, slot) and a contiguous float32 storage layout."""
    arr = np.asarray(face_sources, dtype=np.float32)
    if arr.ndim != 2 or int(arr.shape[1]) != 14:
        raise ValueError("face_sources must be a float32 Nx14 array")
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr, dtype=np.float32)
    return arr


def empty_face_buckets() -> list[np.ndarray]:
    """I define E_i = 0_(0x12) for each face bucket i in {0,...,5}. I use this constructor as the canonical empty realization of split face-source arrays after the metadata columns have been discarded."""
    return empty_face_bucket_arrays(12)


def split_face_sources_to_buckets(face_sources: np.ndarray, bucket_counts: BucketCounts) -> list[np.ndarray]:
    """I define B_i[s,:] = row[:12] whenever row[12] = i and row[13] = s, with every other bucket slot left at zero. I use this scatter to transform the flat source-row stream into six face-indexed payload matrices that match the renderer upload layout."""
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
    """I define R as the concatenation of per-face rows r = (mn, mx, uv, 1, 0, face_idx, slot) over all visible block faces in the chunk iterator. I pair R with the normalized six-face count vector so that later bucket materialization can remain a pure data rearrangement rather than a second visibility walk."""
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
            u0, v0, u1, v1 = atlas_face_uv(atlas, int(fi), face.box, kind=(None if defn is None else str(defn.kind)))

            rows.append([float(mnx), float(mny), float(mnz), float(mxx), float(mxy), float(mxz), float(u0), float(v0), float(u1), float(v1), 1.0, 0.0, float(fi), float(slot)])

    counts = normalize_bucket_counts(bucket_counts)

    if not rows:
        return np.zeros((0, 14), dtype=np.float32), counts

    return np.asarray(rows, dtype=np.float32), counts
