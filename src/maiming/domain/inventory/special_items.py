# FILE: src/maiming/domain/inventory/special_items.py
from __future__ import annotations
from dataclasses import dataclass

OTHELLO_START_ITEM_ID: str = "othello:start"
OTHELLO_SETTINGS_ITEM_ID: str = "othello:settings"

@dataclass(frozen=True)
class SpecialItemDescriptor:
    item_id: str
    display_name: str
    icon_key: str
    description: str

_SPECIAL_ITEMS: dict[str, SpecialItemDescriptor] = {OTHELLO_START_ITEM_ID: SpecialItemDescriptor(item_id=OTHELLO_START_ITEM_ID, display_name="Start", icon_key="start", description="Start or restart the Othello match with the saved settings."), OTHELLO_SETTINGS_ITEM_ID: SpecialItemDescriptor(item_id=OTHELLO_SETTINGS_ITEM_ID, display_name="Settings", icon_key="settings", description="Open the Othello configuration dialog for the next match.")}

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