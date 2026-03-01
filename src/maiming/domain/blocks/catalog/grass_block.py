# FILE: src/maiming/domain/blocks/catalog/grass_block.py
from __future__ import annotations

from maiming.domain.blocks.block_definition import BlockDefinition, BlockTextures
from maiming.domain.blocks.block_registry import BlockRegistry

def register_grass_block(reg: BlockRegistry) -> None:
    tex = BlockTextures(
        pos_x="grass_side_carried",
        neg_x="grass_side_carried",
        pos_y="grass_carried",
        neg_y="dirt",
        pos_z="grass_side_carried",
        neg_z="grass_side_carried",
    )

    reg.register(
        BlockDefinition(
            block_id="minecraft:grass_block",
            display_name="Grass Block",
            textures=tex,
            is_full_cube=True,
            is_solid=True,
        )
    )