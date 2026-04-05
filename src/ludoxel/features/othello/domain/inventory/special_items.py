# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ludoxel.shared.world.inventory.special_item_descriptor import SpecialItemDescriptor

OTHELLO_START_ITEM_ID: str = "othello:start"
OTHELLO_SETTINGS_ITEM_ID: str = "othello:settings"

_OTHELLO_SPECIAL_ITEMS: dict[str, SpecialItemDescriptor] = {OTHELLO_START_ITEM_ID: SpecialItemDescriptor(item_id=OTHELLO_START_ITEM_ID, display_name="Start", icon_key="start", description="Start or restart the Othello match with the saved settings."), OTHELLO_SETTINGS_ITEM_ID: SpecialItemDescriptor(item_id=OTHELLO_SETTINGS_ITEM_ID, display_name="Settings", icon_key="settings", description="Open the Othello configuration dialog for the next match.")}


def iter_othello_special_item_descriptors() -> tuple[SpecialItemDescriptor, ...]:
    return tuple(_OTHELLO_SPECIAL_ITEMS.values())
