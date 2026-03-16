# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/families/special_dirt_types.py
from __future__ import annotations

from ..block_definition import BlockTextures
from .stone_types import StoneType, cube_textures, side_top_bottom_textures

SPECIAL_DIRT_TYPES: tuple[StoneType, ...] = (
    StoneType(key="crimson_nylium", display="Crimson Nylium", textures=side_top_bottom_textures("crimson_nylium_side", "crimson_nylium_top", "netherrack")),
    StoneType(key="warped_nylium", display="Warped Nylium", textures=side_top_bottom_textures("warped_nylium_side", "warped_nylium_top", "netherrack")),
    StoneType(key="netherrack", display="Netherrack", textures=cube_textures("netherrack")),
    StoneType(key="soul_soil", display="Soul Soil", textures=cube_textures("soul_soil")),
    StoneType(key="soul_sand", display="Soul Sand", textures=cube_textures("soul_sand")),
    StoneType(key="grass_block", display="Grass Block", textures=BlockTextures(pos_x="grass_side_carried", neg_x="grass_side_carried", pos_y="grass_carried", neg_y="dirt", pos_z="grass_side_carried", neg_z="grass_side_carried")),
    StoneType(key="podzol", display="Podzol", textures=side_top_bottom_textures("dirt_podzol_side", "dirt_podzol_top", "dirt")),
    StoneType(key="mycelium", display="Mycelium", textures=side_top_bottom_textures("mycelium_side", "mycelium_top", "dirt")),
    StoneType(key="dirt_path", display="Dirt Path", textures=side_top_bottom_textures("dirt_path_side", "dirt_path_top", "dirt"), kind="short_cube", is_full_cube=False),
    StoneType(key="dirt", display="Dirt", textures=cube_textures("dirt")),
    StoneType(key="coarse_dirt", display="Coarse Dirt", textures=cube_textures("coarse_dirt")),
    StoneType(key="rooted_dirt", display="Rooted Dirt", textures=cube_textures("dirt_with_roots")),
    StoneType(key="farmland", display="Farmland", textures=side_top_bottom_textures("dirt", "farmland_dry", "dirt"), kind="short_cube", is_full_cube=False),
    StoneType(key="mud", display="Mud", textures=cube_textures("mud")),
    StoneType(key="clay", display="Clay", textures=cube_textures("clay")),
    StoneType(key="gravel", display="Gravel", textures=cube_textures("gravel")),
    StoneType(key="sand", display="Sand", textures=cube_textures("sand")),
    StoneType(key="red_sand", display="Red Sand", textures=cube_textures("red_sand")),
)
