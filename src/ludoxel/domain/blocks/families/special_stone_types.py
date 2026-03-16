# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/families/special_stone_types.py
from __future__ import annotations

from .stone_types import StoneType, cube_textures, side_top_bottom_textures, column_textures

SPECIAL_STONE_TYPES: tuple[StoneType, ...] = (
    StoneType(key="cobblestone", display="Cobblestone", textures=cube_textures("cobblestone"), slab_key="cobblestone_slab", stairs_key="cobblestone_stairs", wall_key="cobblestone_wall"),
    StoneType(key="mossy_cobblestone", display="Mossy Cobblestone", textures=cube_textures("cobblestone_mossy"), slab_key="mossy_cobblestone_slab", stairs_key="mossy_cobblestone_stairs", wall_key="mossy_cobblestone_wall"),
    StoneType(key="cobbled_deepslate", display="Cobbled Deepslate", textures=cube_textures("cobbled_deepslate"), slab_key="cobbled_deepslate_slab", stairs_key="cobbled_deepslate_stairs", wall_key="cobbled_deepslate_wall"),
    StoneType(key="resin_block", display="Block of Resin", textures=cube_textures("resin_block")),
    StoneType(key="resin_bricks", display="Resin Bricks", textures=cube_textures("resin_bricks"), slab_key="resin_brick_slab", stairs_key="resin_brick_stairs", wall_key="resin_brick_wall"),
    StoneType(key="chiseled_resin_bricks", display="Chiseled Resin Bricks", textures=cube_textures("chiseled_resin_bricks")),
    StoneType(key="nether_bricks", display="Nether Bricks", textures=cube_textures("nether_brick"), slab_key="nether_brick_slab", stairs_key="nether_brick_stairs", wall_key="nether_brick_wall", fence_key="nether_brick_fence"),
    StoneType(key="red_nether_bricks", display="Red Nether Bricks", textures=cube_textures("red_nether_brick"), slab_key="red_nether_brick_slab", stairs_key="red_nether_brick_stairs", wall_key="red_nether_brick_wall"),
    StoneType(key="chiseled_nether_bricks", display="Chiseled Nether Bricks", textures=cube_textures("chiseled_nether_bricks")),
    StoneType(key="cracked_nether_bricks", display="Cracked Nether Bricks", textures=cube_textures("cracked_nether_bricks")),
    StoneType(key="netherite_block", display="Block of Netherite", textures=cube_textures("netherite_block")),
    StoneType(key="lodestone", display="Lodestone", textures=side_top_bottom_textures("lodestone_side", "lodestone_top", "lodestone_top")),
    StoneType(key="purpur_block", display="Purpur Block", textures=cube_textures("purpur_block"), slab_key="purpur_slab", stairs_key="purpur_stairs"),
    StoneType(key="purpur_pillar", display="Purpur Pillar", textures=column_textures("purpur_pillar", "purpur_pillar_top")),
    StoneType(key="honeycomb_block", display="Honeycomb Block", textures=cube_textures("honeycomb")),
    StoneType(key="dark_prismarine", display="Dark Prismarine", textures=cube_textures("prismarine_dark"), slab_key="dark_prismarine_slab", stairs_key="dark_prismarine_stairs"),
    StoneType(key="prismarine_bricks", display="Prismarine Bricks", textures=cube_textures("prismarine_bricks"), slab_key="prismarine_brick_slab", stairs_key="prismarine_brick_stairs"),
    StoneType(key="prismarine", display="Prismarine", textures=cube_textures("prismarine_rough_01"), slab_key="prismarine_slab", stairs_key="prismarine_stairs"),
    StoneType(key="quartz_block", display="Block of Quartz", textures=side_top_bottom_textures("quartz_block_side", "quartz_block_top", "quartz_block_bottom")),
    StoneType(key="quartz_bricks", display="Quartz Bricks", textures=cube_textures("quartz_bricks")),
    StoneType(key="quartz_pillar", display="Quartz Pillar", textures=column_textures("quartz_column_side", "quartz_column_top")),
    StoneType(key="chiseled_quartz_block", display="Chiseled Quartz Block", textures=side_top_bottom_textures("quartz_block_chiseled", "quartz_block_chiseled_top", "quartz_block_chiseled_top")),
    StoneType(key="smooth_quartz", display="Smooth Quartz Block", textures=cube_textures("smooth_quartz"), slab_key="smooth_quartz_slab", stairs_key="smooth_quartz_stairs"),
    StoneType(key="iron_block", display="Block of Iron", textures=cube_textures("iron_block")),
    StoneType(key="coal_block", display="Block of Coal", textures=cube_textures("coal_block")),
    StoneType(key="gold_block", display="Block of Gold", textures=cube_textures("gold_block")),
    StoneType(key="emerald_block", display="Block of Emerald", textures=cube_textures("emerald_block")),
    StoneType(key="diamond_block", display="Block of Diamond", textures=cube_textures("diamond_block")),
    StoneType(key="lapis_block", display="Block of Lapis Lazuli", textures=cube_textures("lapis_block")),
    StoneType(key="raw_copper_block", display="Block of Raw Copper", textures=cube_textures("raw_copper_block")),
    StoneType(key="raw_iron_block", display="Block of Raw Iron", textures=cube_textures("raw_iron_block")),
    StoneType(key="raw_gold_block", display="Block of Raw Gold", textures=cube_textures("raw_gold_block")),
    StoneType(key="calcite", display="Calcite", textures=cube_textures("calcite")),
    StoneType(key="magma_block", display="Magma Block", textures=cube_textures("magma_01")),
    StoneType(key="end_stone", display="End Stone", textures=cube_textures("end_stone")),
    StoneType(key="obsidian", display="Obsidian", textures=cube_textures("obsidian")),
    StoneType(key="crying_obsidian", display="Crying Obsidian", textures=cube_textures("crying_obsidian")),
    StoneType(key="bedrock", display="Bedrock", textures=cube_textures("bedrock")),
)
