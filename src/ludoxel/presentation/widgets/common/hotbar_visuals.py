# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from ....shared.domain.blocks.registry.block_registry import BlockRegistry
from ....features.othello.domain.inventory.special_items import get_special_item_descriptor

def _block_display_name(registry: BlockRegistry, block_id: str | None) -> str:
    bid = "" if block_id is None else str(block_id).strip()
    if not bid:
        return "Empty Hand"

    special = get_special_item_descriptor(bid)
    if special is not None:
        return str(special.display_name)

    block = registry.get(bid)
    if block is None:
        return bid
    return str(block.display_name)

def hotbar_slot_tooltip(registry: BlockRegistry, *, slot_index: int, block_id: str | None) -> str:
    bid = "" if block_id is None else str(block_id).strip()
    if not bid:
        return f"Hotbar Slot {int(slot_index) + 1}\nEmpty Hand"
    return f"Hotbar Slot {int(slot_index) + 1}\n{_block_display_name(registry, bid)}\n{bid}"