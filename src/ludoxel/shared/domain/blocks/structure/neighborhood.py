# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Callable

GetState = Callable[[int, int, int], str | None]

def state_or_empty(get_state: GetState, x: int, y: int, z: int) -> str:
    state = get_state(int(x), int(y), int(z))
    if state is None:
        return ""
    return str(state)

def six_neighbor_state_signature(get_state: GetState, x: int, y: int, z: int) -> tuple[str, str, str, str, str, str]:
    sx = int(x)
    sy = int(y)
    sz = int(z)
    return (state_or_empty(get_state, sx + 1, sy, sz), state_or_empty(get_state, sx - 1, sy, sz), state_or_empty(get_state, sx, sy + 1, sz), state_or_empty(get_state, sx, sy - 1, sz), state_or_empty(get_state, sx, sy, sz + 1), state_or_empty(get_state, sx, sy, sz - 1))