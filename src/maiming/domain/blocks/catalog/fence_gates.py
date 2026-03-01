# FILE: src/maiming/domain/blocks/catalog/fence_gates.py
from __future__ import annotations

from maiming.domain.blocks.block_definition import BlockDefinition, BlockTextures
from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.families.wood_types import WOOD_TYPES, fence_gate_id

def register_fence_gates(reg: BlockRegistry) -> None:
    for w in WOOD_TYPES:
        tex = BlockTextures(
            pos_x=w.texture,
            neg_x=w.texture,
            pos_y=w.texture,
            neg_y=w.texture,
            pos_z=w.texture,
            neg_z=w.texture,
        )
        reg.register(
            BlockDefinition(
                block_id=fence_gate_id(w),
                display_name=f"{w.display} Fence Gate",
                textures=tex,
                kind="fence_gate",
                is_full_cube=False,
                is_solid=True,
                tags=("fence_gate", "wood"),
            )
        )