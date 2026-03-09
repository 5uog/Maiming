# FILE: src/maiming/infrastructure/rendering/opengl/facade/world_mesh_builder.py
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.infrastructure.rendering.opengl._internal.scene.world_face_source_builder import (
    BucketCounts,
    build_chunk_face_sources,
    split_face_sources_to_buckets,
)

UVRect = tuple[float, float, float, float]
UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]
GetState = Callable[[int, int, int], str | None]

def _copy_face_buckets(face_buckets: list[np.ndarray]) -> list[np.ndarray]:
    out: list[np.ndarray] = []

    for arr in face_buckets:
        if arr.size <= 0:
            out.append(np.zeros((0, 12), dtype=np.float32))
            continue

        src = arr
        if src.dtype != np.float32:
            src = src.astype(np.float32, copy=False)
        if not src.flags["C_CONTIGUOUS"]:
            src = np.ascontiguousarray(src, dtype=np.float32)
        else:
            src = src.copy()

        out.append(src)

    return out

def build_chunk_face_payload_sources(
    *,
    blocks: Iterable[tuple[int, int, int, str]],
    get_state: GetState,
    uv_lookup: UVLookup,
    def_lookup: DefLookup,
) -> tuple[np.ndarray, BucketCounts]:
    return build_chunk_face_sources(
        blocks=blocks,
        get_state=get_state,
        uv_lookup=uv_lookup,
        def_lookup=def_lookup,
    )

def build_chunk_mesh_cpu(
    *,
    blocks: Iterable[tuple[int, int, int, str]],
    get_state: GetState,
    uv_lookup: UVLookup,
    def_lookup: DefLookup,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    face_sources, bucket_counts = build_chunk_face_payload_sources(
        blocks=blocks,
        get_state=get_state,
        uv_lookup=uv_lookup,
        def_lookup=def_lookup,
    )

    faces_np = split_face_sources_to_buckets(face_sources, bucket_counts)
    shadow_faces_np = _copy_face_buckets(faces_np)
    return faces_np, shadow_faces_np