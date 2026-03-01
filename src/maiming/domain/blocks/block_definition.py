# FILE: src/maiming/domain/blocks/block_definition.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

FACE_POS_X: int = 0
FACE_NEG_X: int = 1
FACE_POS_Y: int = 2
FACE_NEG_Y: int = 3
FACE_POS_Z: int = 4
FACE_NEG_Z: int = 5

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
    is_full_cube: bool = True
    is_solid: bool = True
    tags: Tuple[str, ...] = ()

    def texture_for_face(self, face_idx: int) -> str:
        return self.textures.texture_for_face(int(face_idx))

    def has_tag(self, tag: str) -> bool:
        t = str(tag)
        return any(str(x) == t for x in self.tags)