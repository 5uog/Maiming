# FILE: src/maiming/domain/blocks/structural_rules.py
from __future__ import annotations

from typing import Callable

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.domain.blocks.state_codec import parse_state

DefLookup = Callable[[str], BlockDefinition | None]

def is_full_solid(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    return bool(defn.is_full_cube) and bool(defn.is_solid)

def is_wall(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    return str(defn.kind) == "wall" or defn.has_tag("wall")

def is_fence(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    return str(defn.kind) == "fence" or defn.has_tag("fence")

def is_fence_gate(defn: BlockDefinition | None) -> bool:
    if defn is None:
        return False
    return str(defn.kind) == "fence_gate" or defn.has_tag("fence_gate")

def fence_gate_connects_to_side(*, facing: str, side_from_gate: str) -> bool:
    f = str(facing)
    s = str(side_from_gate)

    if f in ("north", "south"):
        return s in ("east", "west")
    if f in ("east", "west"):
        return s in ("north", "south")
    return s in ("east", "west")

def wall_side_from_neighbor_state(
    state_str: str | None,
    *,
    side_from_neighbor: str,
    get_def: DefLookup,
) -> str:
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
        if fence_gate_connects_to_side(
            facing=str(facing),
            side_from_gate=str(side_from_neighbor),
        ):
            return "low"
        return "none"

    if is_full_solid(nd):
        return "tall"

    return "none"

def wall_up_rule(
    *,
    north: str,
    east: str,
    south: str,
    west: str,
    above_def: BlockDefinition | None,
) -> bool:
    if is_full_solid(above_def) or is_wall(above_def):
        return True

    ns_line = (north != "none") and (south != "none") and (east == "none") and (west == "none")
    ew_line = (east != "none") and (west != "none") and (north == "none") and (south == "none")

    if ns_line and (str(north) == str(south)):
        return False
    if ew_line and (str(east) == str(west)):
        return False
    return True