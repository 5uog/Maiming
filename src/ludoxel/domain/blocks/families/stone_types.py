# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/families/stone_types.py
from __future__ import annotations

from dataclasses import dataclass

from ..block_definition import BlockTextures


@dataclass(frozen=True)
class StoneType:
    key: str
    display: str
    textures: BlockTextures

    slab_key: str | None = None
    stairs_key: str | None = None
    wall_key: str | None = None
    fence_key: str | None = None

    kind: str = "cube"
    is_full_cube: bool = True


def cube_textures(name: str) -> BlockTextures:
    s = str(name)
    return BlockTextures(pos_x=s, neg_x=s, pos_y=s, neg_y=s, pos_z=s, neg_z=s)


def side_top_bottom_textures(side: str, top: str, bottom: str) -> BlockTextures:
    sx = str(side)
    sy = str(top)
    sb = str(bottom)
    return BlockTextures(pos_x=sx, neg_x=sx, pos_y=sy, neg_y=sb, pos_z=sx, neg_z=sx)


def column_textures(side: str, top: str) -> BlockTextures:
    return side_top_bottom_textures(str(side), str(top), str(top))


def block_id(v: StoneType) -> str:
    return f"minecraft:{v.key}"


def slab_id(v: StoneType) -> str | None:
    if v.slab_key is None:
        return None
    return f"minecraft:{v.slab_key}"


def stairs_id(v: StoneType) -> str | None:
    if v.stairs_key is None:
        return None
    return f"minecraft:{v.stairs_key}"


def wall_id(v: StoneType) -> str | None:
    if v.wall_key is None:
        return None
    return f"minecraft:{v.wall_key}"


def fence_id(v: StoneType) -> str | None:
    if v.fence_key is None:
        return None
    return f"minecraft:{v.fence_key}"


STONE_TYPES: tuple[StoneType, ...] = (
    StoneType(key="stone", display="Stone", textures=cube_textures("stone"), slab_key="stone_slab", stairs_key="stone_stairs"),
    StoneType(key="granite", display="Granite", textures=cube_textures("stone_granite"), slab_key="granite_slab", stairs_key="granite_stairs", wall_key="granite_wall"),
    StoneType(key="diorite", display="Diorite", textures=cube_textures("stone_diorite"), slab_key="diorite_slab", stairs_key="diorite_stairs", wall_key="diorite_wall"),
    StoneType(key="andesite", display="Andesite", textures=cube_textures("stone_andesite"), slab_key="andesite_slab", stairs_key="andesite_stairs", wall_key="andesite_wall"),
    StoneType(key="blackstone", display="Blackstone", textures=cube_textures("blackstone"), slab_key="blackstone_slab", stairs_key="blackstone_stairs", wall_key="blackstone_wall"),
    StoneType(key="deepslate", display="Deepslate", textures=side_top_bottom_textures("deepslate", "deepslate_top", "deepslate_top")),
    StoneType(key="tuff", display="Tuff", textures=cube_textures("tuff"), slab_key="tuff_slab", stairs_key="tuff_stairs", wall_key="tuff_wall"),
    StoneType(key="basalt", display="Basalt", textures=column_textures("basalt_side", "basalt_top")),
    StoneType(key="polished_granite", display="Polished Granite", textures=cube_textures("stone_granite_smooth"), slab_key="polished_granite_slab", stairs_key="polished_granite_stairs"),
    StoneType(key="polished_diorite", display="Polished Diorite", textures=cube_textures("stone_diorite_smooth"), slab_key="polished_diorite_slab", stairs_key="polished_diorite_stairs"),
    StoneType(key="polished_andesite", display="Polished Andesite", textures=cube_textures("stone_andesite_smooth"), slab_key="polished_andesite_slab", stairs_key="polished_andesite_stairs"),
    StoneType(key="polished_blackstone", display="Polished Blackstone", textures=cube_textures("polished_blackstone"), slab_key="polished_blackstone_slab", stairs_key="polished_blackstone_stairs", wall_key="polished_blackstone_wall"),
    StoneType(key="polished_deepslate", display="Polished Deepslate", textures=cube_textures("polished_deepslate"), slab_key="polished_deepslate_slab", stairs_key="polished_deepslate_stairs", wall_key="polished_deepslate_wall"),
    StoneType(key="polished_tuff", display="Polished Tuff", textures=cube_textures("polished_tuff"), slab_key="polished_tuff_slab", stairs_key="polished_tuff_stairs", wall_key="polished_tuff_wall"),
    StoneType(key="polished_basalt", display="Polished Basalt", textures=column_textures("polished_basalt_side", "polished_basalt_top")),
    StoneType(key="smooth_basalt", display="Smooth Basalt", textures=cube_textures("smooth_basalt")),
)
