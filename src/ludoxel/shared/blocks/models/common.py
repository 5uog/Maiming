# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..block_definition import BlockDefinition

@dataclass(frozen=True)
class LocalBox:
    mn_x: float
    mn_y: float
    mn_z: float
    mx_x: float
    mx_y: float
    mx_z: float
    uv_hint: str = ""

    def clamp01(self) -> "LocalBox":

        def c(v: float) -> float:
            return 0.0 if v < 0.0 else 1.0 if v > 1.0 else float(v)

        return LocalBox(mn_x=c(self.mn_x), mn_y=c(self.mn_y), mn_z=c(self.mn_z), mx_x=c(self.mx_x), mx_y=c(self.mx_y), mx_z=c(self.mx_z), uv_hint=str(self.uv_hint))

GetState = Callable[[int, int, int], str | None]
GetDef = Callable[[str], BlockDefinition | None]

def _rot_y_cw(p_x: float, p_z: float, turns: int) -> tuple[float, float]:
    t = int(turns) & 3
    x = float(p_x)
    z = float(p_z)

    if t == 0:
        return x, z
    if t == 1:
        return 1.0 - z, x
    if t == 2:
        return 1.0 - x, 1.0 - z
    return z, 1.0 - x

def rotate_box_y_cw(b: LocalBox, turns: int) -> LocalBox:
    xs = [b.mn_x, b.mx_x]
    zs = [b.mn_z, b.mx_z]
    pts: list[tuple[float, float]] = []

    for x in xs:
        for z in zs:
            pts.append(_rot_y_cw(x, z, turns))

    mnx = min(p[0] for p in pts)
    mxx = max(p[0] for p in pts)
    mnz = min(p[1] for p in pts)
    mxz = max(p[1] for p in pts)

    return LocalBox(mn_x=mnx, mn_y=b.mn_y, mn_z=mnz, mx_x=mxx, mx_y=b.mx_y, mx_z=mxz, uv_hint=str(b.uv_hint))