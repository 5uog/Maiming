# FILE: src/maiming/domain/inventory/hotbar_defaults.py
from __future__ import annotations

from .hotbar import HOTBAR_SIZE, normalize_hotbar_slots
from .special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID

def default_hotbar_slots(*, size: int = HOTBAR_SIZE) -> tuple[str, ...]:
    return normalize_hotbar_slots(None, size=int(size))

def default_othello_hotbar_slots(*, size: int = HOTBAR_SIZE) -> tuple[str, ...]:
    return normalize_hotbar_slots((OTHELLO_START_ITEM_ID, "", "", "", "", "", "", "", OTHELLO_SETTINGS_ITEM_ID), size=int(size))