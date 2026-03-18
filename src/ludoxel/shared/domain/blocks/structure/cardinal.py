# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/domain/blocks/structure/cardinal.py
from __future__ import annotations

_CARDINALS: tuple[str, str, str, str] = ("north", "east", "south", "west")


def normalize_cardinal(facing: str, default: str="south") -> str:
    s = str(facing).strip().lower()
    if s in _CARDINALS:
        return s

    d = str(default).strip().lower()
    if d in _CARDINALS:
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


def cardinal_from_xz(x: float, z: float, *, default: str="south") -> str:
    fx = float(x)
    fz = float(z)

    if abs(fx) <= 1e-12 and abs(fz) <= 1e-12:
        return normalize_cardinal(str(default), default="south")

    if abs(fx) >= abs(fz):
        return "east" if fx > 0.0 else "west"
    return "south" if fz > 0.0 else "north"


def cardinal_turns_from_facing(facing: str) -> int:
    s = normalize_cardinal(str(facing), default="east")
    if s == "east":
        return 0
    if s == "south":
        return 1
    if s == "west":
        return 2
    return 3


def gate_turns_from_facing(facing: str) -> int:
    s = normalize_cardinal(str(facing), default="south")
    if s == "south":
        return 0
    if s == "west":
        return 1
    if s == "north":
        return 2
    return 3
