# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/structural_rules.py
from __future__ import annotations

from typing import Callable

from .block_definition import BlockDefinition
from .state_codec import parse_state
from .state_values import slab_type_value

DefLookup = Callable[[str], BlockDefinition | None]


def is_full_solid(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    return bool(defn.is_full_cube) and bool(defn.is_solid)


def _is_family(defn: BlockDefinition | None, family: str) -> bool:
    if defn is None:
        return False
    return defn.is_family(str(family))


def is_slab(defn: BlockDefinition | None) -> bool:
    return _is_family(defn, "slab")


def is_stairs(defn: BlockDefinition | None) -> bool:
    return _is_family(defn, "stairs")


def is_wall(defn: BlockDefinition | None) -> bool:
    return _is_family(defn, "wall")


def is_fence(defn: BlockDefinition | None) -> bool:
    return _is_family(defn, "fence")


def is_fence_gate(defn: BlockDefinition | None) -> bool:
    return _is_family(defn, "fence_gate")


def _state_is_full_solid_parts(defn: BlockDefinition | None, props: dict[str, str]) -> bool:
    if defn is None:
        return False

    if is_full_solid(defn):
        return True

    if is_slab(defn) and slab_type_value(props) == "double":
        return True

    return False


def block_state_is_full_solid(state_str: str | None, *, get_def: DefLookup) -> bool:
    if state_str is None:
        return False

    base, props = parse_state(str(state_str))
    defn = get_def(str(base))
    return _state_is_full_solid_parts(defn, props)


def fence_gate_connects_to_side(*, facing: str, side_from_gate: str) -> bool:
    f = str(facing)
    s = str(side_from_gate)

    if f in ("north", "south"):
        return s in ("east", "west")
    if f in ("east", "west"):
        return s in ("north", "south")
    return s in ("east", "west")


def fence_connects_to_neighbor_state(state_str: str | None, *, side_from_neighbor: str, get_def: DefLookup) -> bool:
    if state_str is None:
        return False

    base, props = parse_state(str(state_str))
    nd = get_def(str(base))
    if nd is None:
        return True

    if _state_is_full_solid_parts(nd, props) or is_fence(nd):
        return True

    if is_fence_gate(nd):
        facing = str(props.get("facing", "south"))
        return fence_gate_connects_to_side(facing=str(facing), side_from_gate=str(side_from_neighbor))

    return False


def wall_side_from_neighbor_state(state_str: str | None, *, side_from_neighbor: str, get_def: DefLookup) -> str:
    if state_str is None:
        return "none"

    base, props = parse_state(str(state_str))
    nd = get_def(str(base))
    if nd is None:
        return "none"

    if is_wall(nd):
        return "low"

    if is_fence_gate(nd):
        facing = str(props.get("facing", "south"))
        if fence_gate_connects_to_side(facing=str(facing), side_from_gate=str(side_from_neighbor)):
            return "low"
        return "none"

    if _state_is_full_solid_parts(nd, props):
        return "tall"

    return "none"


def wall_up_rule(*, north: str, east: str, south: str, west: str, above_state: str | None, get_def: DefLookup) -> bool:
    if block_state_is_full_solid(above_state, get_def=get_def):
        return True

    if above_state is not None:
        base, _props = parse_state(str(above_state))
        above_def = get_def(str(base))
        if is_wall(above_def):
            return True

    ns_line = (north != "none") and (south != "none") and (east == "none") and (west == "none")
    ew_line = (east != "none") and (west != "none") and (north == "none") and (south == "none")

    if ns_line and (str(north) == str(south)):
        return False
    if ew_line and (str(east) == str(west)):
        return False
    return True
