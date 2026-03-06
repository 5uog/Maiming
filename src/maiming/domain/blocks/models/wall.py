# FILE: src/maiming/domain/blocks/models/wall.py
from __future__ import annotations

from typing import Dict, List

from maiming.domain.blocks.state_codec import parse_state
from maiming.domain.blocks.models.common import LocalBox, GetState, GetDef, rotate_box_y_cw
from maiming.domain.blocks.models.dimensions import (
    WALL_POST,
    WALL_ARM_LOW_NORTH,
    WALL_ARM_TALL_NORTH,
)
from maiming.domain.blocks.structural_rules import (
    wall_side_from_neighbor_state,
    wall_up_rule,
)

def _norm_side(s: str) -> str:
    t = str(s)
    if t in ("none", "low", "tall"):
        return t
    return "none"

def _arm_north(kind: str) -> LocalBox:
    if str(kind) == "tall":
        return WALL_ARM_TALL_NORTH
    return WALL_ARM_LOW_NORTH

def boxes_for_wall(
    *,
    props: Dict[str, str],
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    north = _norm_side(str(props.get("north", ""))) if "north" in props else wall_side_from_neighbor_state(
        get_state(int(x), int(y), int(z - 1)),
        side_from_neighbor="south",
        get_def=get_def,
    )
    east = _norm_side(str(props.get("east", ""))) if "east" in props else wall_side_from_neighbor_state(
        get_state(int(x + 1), int(y), int(z)),
        side_from_neighbor="west",
        get_def=get_def,
    )
    south = _norm_side(str(props.get("south", ""))) if "south" in props else wall_side_from_neighbor_state(
        get_state(int(x), int(y), int(z + 1)),
        side_from_neighbor="north",
        get_def=get_def,
    )
    west = _norm_side(str(props.get("west", ""))) if "west" in props else wall_side_from_neighbor_state(
        get_state(int(x - 1), int(y), int(z)),
        side_from_neighbor="east",
        get_def=get_def,
    )

    if "up" in props:
        up = str(props.get("up", "true")).strip().lower() in ("1", "true", "yes", "on")
    else:
        s_above = get_state(int(x), int(y + 1), int(z))
        above = None
        if s_above is not None:
            b_above, _p_above = parse_state(str(s_above))
            above = get_def(str(b_above))

        up = wall_up_rule(
            north=str(north),
            east=str(east),
            south=str(south),
            west=str(west),
            above_def=above,
        )

    out: list[LocalBox] = []

    if bool(up):
        out.append(WALL_POST)

    if north != "none":
        out.append(_arm_north(north))
    if east != "none":
        out.append(rotate_box_y_cw(_arm_north(east), 1))
    if south != "none":
        out.append(rotate_box_y_cw(_arm_north(south), 2))
    if west != "none":
        out.append(rotate_box_y_cw(_arm_north(west), 3))

    if not out:
        out.append(WALL_POST)

    return out