# FILE: src/maiming/infrastructure/rendering/opengl/facade/world_mesh_builder.py
from __future__ import annotations

from typing import Callable, Iterable

import numpy as np

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.infrastructure.rendering.opengl._internal.scene.world_face_builder import build_chunk_mesh

UVRect = tuple[float, float, float, float]
UVLookup = Callable[[str, int], UVRect]
DefLookup = Callable[[str], BlockDefinition | None]
GetState = Callable[[int, int, int], str | None]

def build_chunk_mesh_cpu(
    *,
    blocks: Iterable[tuple[int, int, int, str]],
    get_state: GetState,
    uv_lookup: UVLookup,
    def_lookup: DefLookup,
) -> tuple[list[np.ndarray], np.ndarray]:
    return build_chunk_mesh(
        blocks=blocks,
        get_state=get_state,
        uv_lookup=uv_lookup,
        def_lookup=def_lookup,
    )