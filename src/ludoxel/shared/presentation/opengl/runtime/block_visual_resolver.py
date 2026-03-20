# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ....domain.blocks.block_definition import BlockDefinition
from ....domain.blocks.registry.block_registry import BlockRegistry
from ....domain.blocks.state.state_codec import parse_state
from ..resources.texture_atlas import TextureAtlas

UVRect = tuple[float, float, float, float]
DefLookup = Callable[[str], BlockDefinition | None]

@dataclass(frozen=True)
class BlockVisualResolver:
    atlas: TextureAtlas
    blocks: BlockRegistry

    def def_lookup(self, base_id: str) -> BlockDefinition | None:
        return self.blocks.get(str(base_id))

    def atlas_uv_face(self, block_state_or_id: str, face_idx: int) -> UVRect:
        base_id, _props = parse_state(str(block_state_or_id))
        block = self.blocks.get(str(base_id))
        tex_name = block.texture_for_face(int(face_idx)) if block is not None else "default"

        uv = self.atlas.uv.get(str(tex_name))
        if uv is None:
            uv = self.atlas.uv.get("default",(0.0, 0.0, 1.0, 1.0))

        return (float(uv[0]), float(uv[1]), float(uv[2]), float(uv[3]))

    def display_name(self, block_state_or_id: str) -> str:
        base_id, _props = parse_state(str(block_state_or_id))
        block = self.blocks.get(str(base_id))
        if block is None:
            return str(base_id)
        return str(block.display_name)

    def world_build_tools(self) -> tuple[Callable[[str, int], UVRect], DefLookup]:
        return (self.atlas_uv_face, self.def_lookup)