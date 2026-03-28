# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from .chunk_face_payload_sources import BucketCounts, build_chunk_face_sources, split_face_sources_to_buckets
from ..render_types import DefLookup, GetState, UVLookup


def _clone_face_buckets(face_buckets: list[np.ndarray]) -> list[np.ndarray]:
    """I define C(B)_i = copy(B_i) for each face bucket i in {0,...,5}. I apply this cloning step when two downstream consumers require equal geometric content but must not share write-coupled ndarray storage."""
    return [np.array(bucket, dtype=np.float32, copy=True, order="C") for bucket in face_buckets]


def build_chunk_face_payload_sources(*, blocks: Iterable[tuple[int, int, int, str]], get_state: GetState, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, BucketCounts]:
    """I define S = BuildSources(blocks, get_state, uv_lookup, def_lookup), where S is the packed Nx14 face-source matrix paired with its six-face bucket counts. I keep this narrow public entry point so that callers that only need source rows do not depend on the later bucket-materialization stage."""
    return build_chunk_face_sources(blocks=blocks, get_state=get_state, uv_lookup=uv_lookup, def_lookup=def_lookup)


def build_chunk_mesh_cpu(*, blocks: Iterable[tuple[int, int, int, str]], get_state: GetState, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """I define M = Split(S_rows, S_counts) and M_shadow = C(M), where S is the face-source payload returned by the source builder. I return two storage-independent six-bucket families because the visible mesh path and the shadow path consume congruent geometry yet may evolve with different later mutation policies."""
    face_sources, bucket_counts = build_chunk_face_payload_sources(blocks=blocks, get_state=get_state, uv_lookup=uv_lookup, def_lookup=def_lookup)
    faces_np = split_face_sources_to_buckets(face_sources, bucket_counts)
    shadow_faces_np = _clone_face_buckets(faces_np)
    return faces_np, shadow_faces_np
