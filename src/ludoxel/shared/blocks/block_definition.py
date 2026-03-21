# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from ..math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z

def _normalize_kind(kind: str) -> str:
    s = str(kind).strip()
    return s if s else "cube"

def _normalize_family(family: str) -> str:
    s = str(family).strip()
    return s if s else "block"

def _normalize_sound_group(sound_group: str) -> str:
    s = str(sound_group).strip()
    return s if s else "block"

@dataclass(frozen=True)
class BlockTextures:
    pos_x: str
    neg_x: str
    pos_y: str
    neg_y: str
    pos_z: str
    neg_z: str

    def texture_for_face(self, face_idx: int) -> str:
        i = int(face_idx)
        if i == FACE_POS_X:
            return str(self.pos_x)
        if i == FACE_NEG_X:
            return str(self.neg_x)
        if i == FACE_POS_Y:
            return str(self.pos_y)
        if i == FACE_NEG_Y:
            return str(self.neg_y)
        if i == FACE_POS_Z:
            return str(self.pos_z)
        if i == FACE_NEG_Z:
            return str(self.neg_z)
        return str(self.pos_y)

@dataclass(frozen=True)
class BlockDefinition:
    block_id: str
    display_name: str
    textures: BlockTextures

    kind: str = "cube"
    family: str = "block"
    is_full_cube: bool = True
    is_solid: bool = True
    tags: Tuple[str, ...] = ()
    sound_group: str = "block"

    def kind_name(self) -> str:
        return _normalize_kind(str(self.kind))

    def family_name(self) -> str:
        return _normalize_family(str(self.family))

    def texture_for_face(self, face_idx: int) -> str:
        return self.textures.texture_for_face(int(face_idx))

    def is_family(self, family: str) -> bool:
        return self.family_name() == _normalize_family(str(family))

    def has_tag(self, tag: str) -> bool:
        t = str(tag)
        return any(str(x) == t for x in self.tags)

    def sound_group_name(self) -> str:
        return _normalize_sound_group(str(self.sound_group))