# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/block_registry.py
from __future__ import annotations

from dataclasses import dataclass

from .block_definition import BlockDefinition


@dataclass
class BlockRegistry:
    _by_id: dict[str, BlockDefinition]
    _sealed: bool

    def __init__(self) -> None:
        self._by_id = {}
        self._sealed = False

    def seal(self) -> None:
        self._sealed = True

    def is_sealed(self) -> bool:
        return bool(self._sealed)

    def register(self, block: BlockDefinition) -> None:
        if self._sealed:
            raise RuntimeError("BlockRegistry is sealed and cannot be mutated")

        bid = str(block.block_id)
        if not bid:
            raise ValueError("block_id must be non-empty")
        if bid in self._by_id:
            raise ValueError(f"Duplicate block_id: {bid}")
        self._by_id[bid] = block

    def get(self, block_id: str) -> BlockDefinition | None:
        return self._by_id.get(str(block_id))

    def all_blocks(self) -> list[BlockDefinition]:
        return [self._by_id[k] for k in sorted(self._by_id.keys())]

    def required_texture_names(self) -> list[str]:
        names: set[str] = set()
        for b in self._by_id.values():
            names.add(str(b.textures.pos_x))
            names.add(str(b.textures.neg_x))
            names.add(str(b.textures.pos_y))
            names.add(str(b.textures.neg_y))
            names.add(str(b.textures.pos_z))
            names.add(str(b.textures.neg_z))

        names.add("default")
        return sorted(names)
