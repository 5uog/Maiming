# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from .hotbar import HOTBAR_SIZE, normalize_hotbar_slots

def default_hotbar_slots(*, size: int=HOTBAR_SIZE) -> tuple[str, ...]:
    return normalize_hotbar_slots(None, size=int(size))