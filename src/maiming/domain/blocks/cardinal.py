# FILE: src/maiming/domain/blocks/cardinal.py
from __future__ import annotations

def normalize_cardinal(facing: str, default: str = "south") -> str:
    s = str(facing)
    if s in ("north", "east", "south", "west"):
        return s

    d = str(default)
    if d in ("north", "east", "south", "west"):
        return d

    return "south"

def opposite_cardinal(facing: str) -> str:
    s = normalize_cardinal(str(facing))
    if s == "north":
        return "south"
    if s == "south":
        return "north"
    if s == "east":
        return "west"
    return "east"

def facing_vec_xz(facing: str) -> tuple[float, float]:
    s = normalize_cardinal(str(facing))
    if s == "north":
        return (0.0, -1.0)
    if s == "south":
        return (0.0, 1.0)
    if s == "east":
        return (1.0, 0.0)
    return (-1.0, 0.0)