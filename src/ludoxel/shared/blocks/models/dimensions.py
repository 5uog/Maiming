# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from .common import LocalBox

def px_box(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float, *, uv_hint: str="") -> LocalBox:
    return LocalBox(mn_x=float(x0) / 16.0, mn_y=float(y0) / 16.0, mn_z=float(z0) / 16.0, mx_x=float(x1) / 16.0, mx_y=float(y1) / 16.0, mx_z=float(z1) / 16.0, uv_hint=str(uv_hint))

FENCE_POST = px_box(6, 0, 6, 10, 16, 10)
FENCE_ARM_LOW_NORTH = px_box(7, 6, 0, 9, 9, 9)
FENCE_ARM_HIGH_NORTH = px_box(7, 12, 0, 9, 15, 9)

FENCE_GATE_CLOSED: list[LocalBox] = [px_box(0, 5, 7, 2, 16, 9, uv_hint="post"), px_box(14, 5, 7, 16, 16, 9, uv_hint="post"), px_box(6, 6, 7, 8, 15, 9, uv_hint="stile"), px_box(8, 6, 7, 10, 15, 9, uv_hint="stile"), px_box(2, 6, 7, 6, 9, 9, uv_hint="rail"), px_box(2, 12, 7, 6, 15, 9, uv_hint="rail"), px_box(10, 6, 7, 14, 9, 9, uv_hint="rail"), px_box(10, 12, 7, 14, 15, 9, uv_hint="rail")]

FENCE_GATE_OPEN: list[LocalBox] = [px_box(0, 5, 7, 2, 16, 9, uv_hint="post"), px_box(14, 5, 7, 16, 16, 9, uv_hint="post"), px_box(0, 6, 13, 2, 15, 15, uv_hint="stile"), px_box(14, 6, 13, 16, 15, 15, uv_hint="stile"), px_box(0, 6, 9, 2, 9, 13, uv_hint="rail"), px_box(0, 12, 9, 2, 15, 13, uv_hint="rail"), px_box(14, 6, 9, 16, 9, 13, uv_hint="rail"), px_box(14, 12, 9, 16, 15, 13, uv_hint="rail")]

def _shift_y(boxes: list[LocalBox], dy_px: float) -> list[LocalBox]:
    dy = float(dy_px) / 16.0
    out: list[LocalBox] = []

    for b in boxes:
        out.append(LocalBox(mn_x=float(b.mn_x), mn_y=float(b.mn_y) + dy, mn_z=float(b.mn_z), mx_x=float(b.mx_x), mx_y=float(b.mx_y) + dy, mx_z=float(b.mx_z), uv_hint=str(b.uv_hint)))
    return out

FENCE_GATE_WALL_CLOSED = _shift_y(FENCE_GATE_CLOSED, -3.0)
FENCE_GATE_WALL_OPEN = _shift_y(FENCE_GATE_OPEN, -3.0)

WALL_POST = px_box(4, 0, 4, 12, 16, 12)
WALL_ARM_LOW_NORTH = px_box(5, 0, 0, 11, 14, 11)
WALL_ARM_TALL_NORTH = px_box(5, 0, 0, 11, 16, 11)