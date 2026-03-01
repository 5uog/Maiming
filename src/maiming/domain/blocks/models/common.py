# FILE: src/maiming/domain/blocks/models/common.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.domain.blocks.state_codec import parse_state

@dataclass(frozen=True)
class LocalBox:
    mn_x: float
    mn_y: float
    mn_z: float
    mx_x: float
    mx_y: float
    mx_z: float

    def clamp01(self) -> "LocalBox":
        def c(v: float) -> float:
            return 0.0 if v < 0.0 else 1.0 if v > 1.0 else float(v)

        return LocalBox(
            mn_x=c(self.mn_x), mn_y=c(self.mn_y), mn_z=c(self.mn_z),
            mx_x=c(self.mx_x), mx_y=c(self.mx_y), mx_z=c(self.mx_z),
        )

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

    return LocalBox(mnx, b.mn_y, mnz, mxx, b.mx_y, mxz)

def cardinal_turns_from_facing(facing: str) -> int:
    f = str(facing)
    if f == "east":
        return 0
    if f == "south":
        return 1
    if f == "west":
        return 2
    if f == "north":
        return 3
    return 0

def gate_turns_from_facing(facing: str) -> int:
    f = str(facing)
    if f == "south":
        return 0
    if f == "west":
        return 1
    if f == "north":
        return 2
    if f == "east":
        return 3
    return 0

def is_full_solid(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    return bool(defn.is_full_cube and defn.is_solid)

def is_fence_like(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    if defn.kind == "fence":
        return True
    if defn.kind == "fence_gate":
        return True
    return defn.has_tag("fence") or defn.has_tag("fence_gate")

def get_neighbor_def(get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> BlockDefinition | None:
    s = get_state(int(x), int(y), int(z))
    if s is None:
        return None
    base, _p = parse_state(s)
    return get_def(str(base))