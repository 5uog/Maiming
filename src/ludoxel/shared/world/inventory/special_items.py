# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ludoxel.features.othello.domain.inventory.special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID, iter_othello_special_item_descriptors

from .core_special_items import AI_ROUTE_CANCEL_ITEM_ID, AI_ROUTE_CONFIRM_ITEM_ID, AI_ROUTE_ERASE_ITEM_ID, AI_SPAWN_EGG_ITEM_ID, iter_core_special_item_descriptors
from .special_item_descriptor import SpecialItemDescriptor

_SPECIAL_ITEMS: dict[str, SpecialItemDescriptor] = {str(descriptor.item_id).strip().lower(): descriptor for descriptor in (*iter_core_special_item_descriptors(), *iter_othello_special_item_descriptors())}


def get_special_item_descriptor(item_id: object) -> SpecialItemDescriptor | None:
    key = str(item_id).strip().lower()
    if not key:
        return None
    return _SPECIAL_ITEMS.get(key)


def is_special_item_id(item_id: object) -> bool:
    return get_special_item_descriptor(item_id) is not None


def special_item_display_name(item_id: object) -> str | None:
    descriptor = get_special_item_descriptor(item_id)
    if descriptor is None:
        return None
    return str(descriptor.display_name)


def iter_special_item_descriptors() -> tuple[SpecialItemDescriptor, ...]:
    return tuple(_SPECIAL_ITEMS.values())


def iter_catalog_special_items() -> tuple[SpecialItemDescriptor, ...]:
    return tuple(descriptor for descriptor in _SPECIAL_ITEMS.values() if bool(descriptor.catalog_visible))


def special_item_icon_keys() -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for descriptor in _SPECIAL_ITEMS.values():
        icon_key = str(descriptor.icon_key).strip()
        if not icon_key or icon_key in seen:
            continue
        seen.add(icon_key)
        ordered.append(icon_key)
    return tuple(ordered)
