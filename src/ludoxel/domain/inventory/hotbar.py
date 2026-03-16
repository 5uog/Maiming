# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/inventory/hotbar.py
from __future__ import annotations

from collections.abc import Sequence

HOTBAR_SIZE: int = 9


def normalize_hotbar_slots(raw: Sequence[object] | None, *, size: int=HOTBAR_SIZE) -> tuple[str, ...]:
    width = int(max(1, int(size)))
    out: list[str] = []

    if raw is not None:
        for value in tuple(raw)[:width]:
            if value is None:
                out.append("")
            else:
                out.append(str(value).strip())

    while len(out) < width:
        out.append("")

    return tuple(out[:width])


def normalize_hotbar_index(index: int, *, size: int=HOTBAR_SIZE) -> int:
    width = int(max(1, int(size)))

    try:
        idx = int(index)
    except Exception:
        idx = 0

    return max(0, min(width - 1, idx))


def cycle_hotbar_index(selected_index: int, delta_steps: int, *, size: int=HOTBAR_SIZE) -> int:
    width = int(max(1, int(size)))
    idx = normalize_hotbar_index(int(selected_index), size=width)
    step = int(delta_steps)

    if step == 0:
        return idx

    return int((idx + step) % width)


def current_hotbar_block_id(slots: Sequence[object] | None, selected_index: int, *, size: int=HOTBAR_SIZE) -> str | None:
    norm = normalize_hotbar_slots(slots, size=int(size))
    idx = normalize_hotbar_index(int(selected_index), size=int(size))
    bid = str(norm[idx]).strip()
    return bid if bid else None


def with_hotbar_assignment(slots: Sequence[object] | None, index: int, block_id: str | None, *, size: int=HOTBAR_SIZE) -> tuple[str, ...]:
    out = list(normalize_hotbar_slots(slots, size=int(size)))
    idx = normalize_hotbar_index(int(index), size=int(size))
    out[idx] = "" if block_id is None else str(block_id).strip()
    return tuple(out)
