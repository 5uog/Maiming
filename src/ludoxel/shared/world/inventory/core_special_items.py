# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from .special_item_descriptor import SpecialItemDescriptor

AI_SPAWN_EGG_ITEM_ID: str = "ludoxel:ai_spawn_egg"
AI_ROUTE_CONFIRM_ITEM_ID: str = "ludoxel:ai_route_confirm"
AI_ROUTE_ERASE_ITEM_ID: str = "ludoxel:ai_route_erase"
AI_ROUTE_CANCEL_ITEM_ID: str = "ludoxel:ai_route_cancel"

_CORE_SPECIAL_ITEMS: dict[str, SpecialItemDescriptor] = {AI_SPAWN_EGG_ITEM_ID: SpecialItemDescriptor(item_id=AI_SPAWN_EGG_ITEM_ID, display_name="AI", icon_key="ai_spawn_egg", description="Spawn one standby AI directly at a valid placement cell. Right-click an existing AI to edit that individual instance.", catalog_visible=True), AI_ROUTE_CONFIRM_ITEM_ID: SpecialItemDescriptor(item_id=AI_ROUTE_CONFIRM_ITEM_ID, display_name="Check", icon_key="route_confirm", description="Commit the current AI route draft."), AI_ROUTE_ERASE_ITEM_ID: SpecialItemDescriptor(item_id=AI_ROUTE_ERASE_ITEM_ID, display_name="Eraser", icon_key="route_erase", description="Focus and delete a route point under the crosshair."), AI_ROUTE_CANCEL_ITEM_ID: SpecialItemDescriptor(item_id=AI_ROUTE_CANCEL_ITEM_ID, display_name="Cancel", icon_key="route_cancel", description="Discard the current AI route draft.")}


def iter_core_special_item_descriptors() -> tuple[SpecialItemDescriptor, ...]:
    return tuple(_CORE_SPECIAL_ITEMS.values())
