# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/families/wood_types.py
from __future__ import annotations

from dataclasses import dataclass

from ..sound_groups import (
    SOUND_GROUP_BAMBOO_WOOD,
    SOUND_GROUP_CHERRY_WOOD,
    SOUND_GROUP_NETHER_WOOD,
    SOUND_GROUP_WOOD,
)


@dataclass(frozen=True)
class WoodType:
    key: str
    display: str
    texture: str
    sound_group: str = SOUND_GROUP_WOOD


WOOD_TYPES: tuple[WoodType, ...] = (
    WoodType("oak", "Oak", "planks_oak", SOUND_GROUP_WOOD),
    WoodType("spruce", "Spruce", "planks_spruce", SOUND_GROUP_WOOD),
    WoodType("birch", "Birch", "planks_birch", SOUND_GROUP_WOOD),
    WoodType("jungle", "Jungle", "planks_jungle", SOUND_GROUP_WOOD),
    WoodType("acacia", "Acacia", "planks_acacia", SOUND_GROUP_WOOD),
    WoodType("dark_oak", "Dark Oak", "planks_big_oak", SOUND_GROUP_WOOD),
    WoodType("mangrove", "Mangrove", "mangrove_planks", SOUND_GROUP_WOOD),
    WoodType("cherry", "Cherry", "cherry_planks", SOUND_GROUP_CHERRY_WOOD),
    WoodType("pale_oak", "Pale Oak", "pale_oak_planks", SOUND_GROUP_WOOD),
    WoodType("bamboo", "Bamboo", "bamboo_planks", SOUND_GROUP_BAMBOO_WOOD),
    WoodType("crimson", "Crimson", "crimson_planks", SOUND_GROUP_NETHER_WOOD),
    WoodType("warped", "Warped", "warped_planks", SOUND_GROUP_NETHER_WOOD),
)

MOSAIC_TYPES: tuple[WoodType, ...] = (
    WoodType("bamboo_mosaic", "Bamboo Mosaic", "bamboo_mosaic", SOUND_GROUP_BAMBOO_WOOD),
)


def planks_id(w: WoodType) -> str:
    if w.key == "bamboo_mosaic":
        return "minecraft:bamboo_mosaic"
    return f"minecraft:{w.key}_planks"


def slab_id(w: WoodType) -> str:
    if w.key == "bamboo_mosaic":
        return "minecraft:bamboo_mosaic_slab"
    return f"minecraft:{w.key}_slab"


def stairs_id(w: WoodType) -> str:
    if w.key == "bamboo_mosaic":
        return "minecraft:bamboo_mosaic_stairs"
    return f"minecraft:{w.key}_stairs"


def fence_id(w: WoodType) -> str:
    return f"minecraft:{w.key}_fence"


def fence_gate_id(w: WoodType) -> str:
    return f"minecraft:{w.key}_fence_gate"
