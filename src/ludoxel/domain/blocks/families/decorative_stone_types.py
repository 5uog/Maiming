# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/families/decorative_stone_types.py
from __future__ import annotations

from ..sound_groups import SOUND_GROUP_DEEPSLATE_BRICKS, SOUND_GROUP_TUFF
from .stone_types import StoneType, cube_textures, side_top_bottom_textures

DECORATIVE_STONE_TYPES: tuple[StoneType, ...] = (
    StoneType(key="stone_bricks", display="Stone Bricks", textures=cube_textures("stonebrick"), slab_key="stone_brick_slab", stairs_key="stone_brick_stairs", wall_key="stone_brick_wall"),
    StoneType(key="mossy_stone_bricks", display="Mossy Stone Bricks", textures=cube_textures("stonebrick_mossy"), slab_key="mossy_stone_brick_slab", stairs_key="mossy_stone_brick_stairs", wall_key="mossy_stone_brick_wall"),
    StoneType(key="cracked_stone_bricks", display="Cracked Stone Bricks", textures=cube_textures("stonebrick_cracked")),
    StoneType(key="chiseled_stone_bricks", display="Chiseled Stone Bricks", textures=cube_textures("stonebrick_carved")),
    StoneType(key="double_smooth_stone_slab", display="Double Smooth Stone Slab", textures=side_top_bottom_textures("stone_slab_side", "stone_slab_top", "stone_slab_top"), slab_key="smooth_stone_slab"),
    StoneType(key="smooth_stone", display="Smooth Stone", textures=cube_textures("stone_slab_top")),
    StoneType(key="end_stone_bricks", display="End Stone Bricks", textures=cube_textures("end_bricks"), slab_key="end_stone_brick_slab", stairs_key="end_stone_brick_stairs", wall_key="end_stone_brick_wall"),
    StoneType(key="polished_blackstone_bricks", display="Polished Blackstone Bricks", textures=cube_textures("polished_blackstone_bricks"), slab_key="polished_blackstone_brick_slab", stairs_key="polished_blackstone_brick_stairs", wall_key="polished_blackstone_brick_wall"),
    StoneType(key="cracked_polished_blackstone_bricks", display="Cracked Polished Blackstone Bricks", textures=cube_textures("cracked_polished_blackstone_bricks")),
    StoneType(key="chiseled_polished_blackstone", display="Chiseled Polished Blackstone", textures=cube_textures("chiseled_polished_blackstone")),
    StoneType(key="deepslate_tiles", display="Deepslate Tiles", textures=cube_textures("deepslate_tiles"), slab_key="deepslate_tile_slab", stairs_key="deepslate_tile_stairs", wall_key="deepslate_tile_wall", sound_group=SOUND_GROUP_DEEPSLATE_BRICKS),
    StoneType(key="cracked_deepslate_tiles", display="Cracked Deepslate Tiles", textures=cube_textures("cracked_deepslate_tiles"), sound_group=SOUND_GROUP_DEEPSLATE_BRICKS),
    StoneType(key="deepslate_bricks", display="Deepslate Bricks", textures=cube_textures("deepslate_bricks"), slab_key="deepslate_brick_slab", stairs_key="deepslate_brick_stairs", wall_key="deepslate_brick_wall", sound_group=SOUND_GROUP_DEEPSLATE_BRICKS),
    StoneType(key="tuff_bricks", display="Tuff Bricks", textures=cube_textures("tuff_bricks"), slab_key="tuff_brick_slab", stairs_key="tuff_brick_stairs", wall_key="tuff_brick_wall", sound_group=SOUND_GROUP_TUFF),
    StoneType(key="cracked_deepslate_bricks", display="Cracked Deepslate Bricks", textures=cube_textures("cracked_deepslate_bricks"), sound_group=SOUND_GROUP_DEEPSLATE_BRICKS),
    StoneType(key="chiseled_deepslate", display="Chiseled Deepslate", textures=cube_textures("chiseled_deepslate"), sound_group=SOUND_GROUP_DEEPSLATE_BRICKS),
    StoneType(key="chiseled_tuff", display="Chiseled Tuff", textures=side_top_bottom_textures("chiseled_tuff", "chiseled_tuff_top", "chiseled_tuff_top"), sound_group=SOUND_GROUP_TUFF),
    StoneType(key="chiseled_tuff_bricks", display="Chiseled Tuff Bricks", textures=side_top_bottom_textures("chiseled_tuff_bricks", "chiseled_tuff_bricks_top", "chiseled_tuff_bricks_top"), sound_group=SOUND_GROUP_TUFF),
)
