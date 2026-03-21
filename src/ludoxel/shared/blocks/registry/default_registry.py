# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from threading import Lock

from ludoxel.shared.blocks.registry.block_registry import BlockRegistry

_DEFAULT_REGISTRY: BlockRegistry | None = None
_DEFAULT_REGISTRY_LOCK = Lock()

def _build_default_registry() -> BlockRegistry:
    reg = BlockRegistry()

    from ludoxel.shared.blocks.catalog.planks import register_wood_blocks
    from ludoxel.shared.blocks.catalog.stones import register_stones

    register_wood_blocks(reg)
    register_stones(reg)

    reg.seal()
    return reg

def create_default_registry() -> BlockRegistry:
    global _DEFAULT_REGISTRY

    reg = _DEFAULT_REGISTRY
    if reg is not None:
        return reg

    with _DEFAULT_REGISTRY_LOCK:
        reg = _DEFAULT_REGISTRY
        if reg is None:
            reg = _build_default_registry()
            _DEFAULT_REGISTRY = reg
        return reg