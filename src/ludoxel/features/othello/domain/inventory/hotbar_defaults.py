# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from .....shared.world.inventory.hotbar import HOTBAR_SIZE, normalize_hotbar_slots
from .special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID

def default_othello_hotbar_slots(*, size: int=HOTBAR_SIZE) -> tuple[str, ...]:
    return normalize_hotbar_slots((OTHELLO_START_ITEM_ID, "", "", "", "", "", "", "", OTHELLO_SETTINGS_ITEM_ID), size=int(size))