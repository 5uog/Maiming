# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/catalog/planks.py
from __future__ import annotations

from ..block_definition import BlockTextures
from ..block_registry import BlockRegistry
from ..families.wood_types import (
    MOSAIC_TYPES,
    WOOD_TYPES,
    WoodType,
    fence_gate_id,
    fence_id,
    planks_id,
    slab_id,
    stairs_id,
)
from .variant_recipes import CatalogVariantRecipe, register_catalog_variants

_WOOD_TAGS = ("wood",)
_PLANK_TAGS = ("planks", "wood")


def _wood_textures(w: WoodType) -> BlockTextures:
    tex = str(w.texture)
    return BlockTextures(pos_x=tex, neg_x=tex, pos_y=tex, neg_y=tex, pos_z=tex, neg_z=tex)


def _all_plank_variants() -> tuple[WoodType, ...]:
    return WOOD_TYPES + MOSAIC_TYPES


_PLANK_RECIPE = CatalogVariantRecipe(
    variant_id=lambda wood: planks_id(wood),
    display_name=lambda wood: f"{wood.display} Planks" if wood.key != "bamboo_mosaic" else str(wood.display),
    kind="cube",
    family="block",
    is_full_cube=True,
)
_SLAB_RECIPE = CatalogVariantRecipe(
    variant_id=lambda wood: slab_id(wood),
    display_name=lambda wood: f"{wood.display} Slab" if wood.key != "bamboo_mosaic" else "Bamboo Mosaic Slab",
    kind="slab",
    family="slab",
    is_full_cube=False,
)
_STAIR_RECIPE = CatalogVariantRecipe(
    variant_id=lambda wood: stairs_id(wood),
    display_name=lambda wood: f"{wood.display} Stairs" if wood.key != "bamboo_mosaic" else "Bamboo Mosaic Stairs",
    kind="stairs",
    family="stairs",
    is_full_cube=False,
)
_FENCE_RECIPE = CatalogVariantRecipe(
    variant_id=lambda wood: fence_id(wood),
    display_name=lambda wood: f"{wood.display} Fence",
    kind="fence",
    family="fence",
    is_full_cube=False,
)
_FENCE_GATE_RECIPE = CatalogVariantRecipe(
    variant_id=lambda wood: fence_gate_id(wood),
    display_name=lambda wood: f"{wood.display} Fence Gate",
    kind="fence_gate",
    family="fence_gate",
    is_full_cube=False,
)


def register_planks(reg: BlockRegistry) -> None:
    for w in _all_plank_variants():
        register_catalog_variants(
            reg,
            w,
            textures=_wood_textures(w),
            tags=_PLANK_TAGS,
            recipes=(_PLANK_RECIPE,),
            sound_group=lambda wood: getattr(wood, "sound_group", "wood"),
        )


def register_slabs(reg: BlockRegistry) -> None:
    for w in _all_plank_variants():
        register_catalog_variants(
            reg,
            w,
            textures=_wood_textures(w),
            tags=_WOOD_TAGS,
            recipes=(_SLAB_RECIPE,),
            sound_group=lambda wood: getattr(wood, "sound_group", "wood"),
        )


def register_stairs(reg: BlockRegistry) -> None:
    for w in _all_plank_variants():
        register_catalog_variants(
            reg,
            w,
            textures=_wood_textures(w),
            tags=_WOOD_TAGS,
            recipes=(_STAIR_RECIPE,),
            sound_group=lambda wood: getattr(wood, "sound_group", "wood"),
        )


def register_fences(reg: BlockRegistry) -> None:
    for w in WOOD_TYPES:
        register_catalog_variants(
            reg,
            w,
            textures=_wood_textures(w),
            tags=_WOOD_TAGS,
            recipes=(_FENCE_RECIPE,),
            sound_group=lambda wood: getattr(wood, "sound_group", "wood"),
        )


def register_fence_gates(reg: BlockRegistry) -> None:
    for w in WOOD_TYPES:
        register_catalog_variants(
            reg,
            w,
            textures=_wood_textures(w),
            tags=_WOOD_TAGS,
            recipes=(_FENCE_GATE_RECIPE,),
            sound_group=lambda wood: getattr(wood, "sound_group", "wood"),
        )


def register_wood_blocks(reg: BlockRegistry) -> None:
    register_planks(reg)
    register_slabs(reg)
    register_stairs(reg)
    register_fences(reg)
    register_fence_gates(reg)
