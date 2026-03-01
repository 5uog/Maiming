# FILE: src/maiming/domain/blocks/catalog/planks.py
from __future__ import annotations

from maiming.domain.blocks.block_definition import BlockDefinition, BlockTextures
from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.families.wood_types import WOOD_TYPES, MOSAIC_TYPES, planks_id

def register_planks(reg: BlockRegistry) -> None:
    for w in WOOD_TYPES + MOSAIC_TYPES:
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
                block_id=planks_id(w),
                display_name=f"{w.display} Planks" if w.key != "bamboo_mosaic" else w.display,
                textures=tex,
                kind="cube",
                is_full_cube=True,
                is_solid=True,
                tags=("planks", "wood"),
            )
        )