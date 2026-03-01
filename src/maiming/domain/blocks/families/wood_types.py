# FILE: src/maiming/domain/blocks/families/wood_types.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class WoodType:
    key: str
    display: str
    texture: str

WOOD_TYPES: tuple[WoodType, ...] = (
    WoodType("oak", "Oak", "planks_oak"),
    WoodType("spruce", "Spruce", "planks_spruce"),
    WoodType("birch", "Birch", "planks_birch"),
    WoodType("jungle", "Jungle", "planks_jungle"),
    WoodType("acacia", "Acacia", "planks_acacia"),
    WoodType("dark_oak", "Dark Oak", "planks_big_oak"),
    WoodType("mangrove", "Mangrove", "mangrove_planks"),
    WoodType("cherry", "Cherry", "cherry_planks"),
    WoodType("pale_oak", "Pale Oak", "pale_oak_planks"),
    WoodType("bamboo", "Bamboo", "bamboo_planks"),
    WoodType("crimson", "Crimson", "crimson_planks"),
    WoodType("warped", "Warped", "warped_planks"),
)

MOSAIC_TYPES: tuple[WoodType, ...] = (
    WoodType("bamboo_mosaic", "Bamboo Mosaic", "bamboo_mosaic"),
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