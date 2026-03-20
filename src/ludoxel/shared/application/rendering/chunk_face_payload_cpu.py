# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/application/rendering/chunk_face_payload_cpu.py
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np

from ...domain.blocks.block_definition import BlockDefinition
from .chunk_face_payload_sources import BucketCounts, build_chunk_face_sources, split_face_sources_to_buckets

UVRect = tuple[float, float, float, float]
UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]
GetState = Callable[[int, int, int], str | None]


def build_chunk_face_payload_sources(*, blocks: Iterable[tuple[int, int, int, str]], get_state: GetState, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, BucketCounts]:
    return build_chunk_face_sources(blocks=blocks, get_state=get_state, uv_lookup=uv_lookup, def_lookup=def_lookup)


def build_chunk_mesh_cpu(*, blocks: Iterable[tuple[int, int, int, str]], get_state: GetState, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[list[np.ndarray], list[np.ndarray]]:
    face_sources, bucket_counts = build_chunk_face_payload_sources(blocks=blocks, get_state=get_state, uv_lookup=uv_lookup, def_lookup=def_lookup)

    faces_np = split_face_sources_to_buckets(face_sources, bucket_counts)
    shadow_faces_np = list(faces_np)
    return faces_np, shadow_faces_np
