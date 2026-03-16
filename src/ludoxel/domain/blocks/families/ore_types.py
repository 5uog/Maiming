# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/families/ore_types.py
from __future__ import annotations

from .stone_types import StoneType, cube_textures, column_textures

ORE_TYPES: tuple[StoneType, ...] = (
    StoneType(key="iron_ore", display="Iron Ore", textures=cube_textures("iron_ore")),
    StoneType(key="gold_ore", display="Gold Ore", textures=cube_textures("gold_ore")),
    StoneType(key="diamond_ore", display="Diamond Ore", textures=cube_textures("diamond_ore")),
    StoneType(key="lapis_ore", display="Lapis Ore", textures=cube_textures("lapis_ore")),
    StoneType(key="redstone_ore", display="Redstone Ore", textures=cube_textures("redstone_ore")),
    StoneType(key="coal_ore", display="Coal Ore", textures=cube_textures("coal_ore")),
    StoneType(key="copper_ore", display="Copper Ore", textures=cube_textures("copper_ore")),
    StoneType(key="emerald_ore", display="Emerald Ore", textures=cube_textures("emerald_ore")),
    StoneType(key="nether_quartz_ore", display="Nether Quartz Ore", textures=cube_textures("quartz_ore")),
    StoneType(key="nether_gold_ore", display="Nether Gold Ore", textures=cube_textures("nether_gold_ore")),
    StoneType(key="ancient_debris", display="Ancient Debris", textures=column_textures("ancient_debris_side", "ancient_debris_top")),
    StoneType(key="deepslate_iron_ore", display="Deepslate Iron Ore", textures=cube_textures("deepslate_iron_ore")),
    StoneType(key="deepslate_gold_ore", display="Deepslate Gold Ore", textures=cube_textures("deepslate_gold_ore")),
    StoneType(key="deepslate_diamond_ore", display="Deepslate Diamond Ore", textures=cube_textures("deepslate_diamond_ore")),
    StoneType(key="deepslate_lapis_ore", display="Deepslate Lapis Ore", textures=cube_textures("deepslate_lapis_ore")),
    StoneType(key="deepslate_redstone_ore", display="Deepslate Redstone Ore", textures=cube_textures("deepslate_redstone_ore")),
    StoneType(key="deepslate_emerald_ore", display="Deepslate Emerald Ore", textures=cube_textures("deepslate_emerald_ore")),
    StoneType(key="deepslate_coal_ore", display="Deepslate Coal Ore", textures=cube_textures("deepslate_coal_ore")),
    StoneType(key="deepslate_copper_ore", display="Deepslate Copper Ore", textures=cube_textures("deepslate_copper_ore")),
)
