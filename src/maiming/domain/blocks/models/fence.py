# FILE: src/maiming/domain/blocks/models/fence.py
from __future__ import annotations

from typing import List

from maiming.domain.blocks.cardinal import opposite_cardinal
from maiming.domain.blocks.models.common import LocalBox, GetState, GetDef, rotate_box_y_cw
from maiming.domain.blocks.models.dimensions import (
    FENCE_POST,
    FENCE_ARM_LOW_NORTH,
    FENCE_ARM_HIGH_NORTH,
)
from maiming.domain.blocks.structural_rules import fence_connects_to_neighbor_state

def boxes_for_fence(
    *,
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    connections = {"north": False, "south": False, "east": False, "west": False}

    for d, (dx, dz) in (("north", (0, -1)), ("south", (0, 1)), ("east", (1, 0)), ("west", (-1, 0))):
        s = get_state(int(x + dx), int(y), int(z + dz))
        connections[d] = fence_connects_to_neighbor_state(
            s,
            side_from_neighbor=opposite_cardinal(str(d)),
            get_def=get_def,
        )

    boxes = [FENCE_POST]

    if connections["north"]:
        boxes.append(FENCE_ARM_LOW_NORTH)
        boxes.append(FENCE_ARM_HIGH_NORTH)
    if connections["east"]:
        boxes.append(rotate_box_y_cw(FENCE_ARM_LOW_NORTH, 1))
        boxes.append(rotate_box_y_cw(FENCE_ARM_HIGH_NORTH, 1))
    if connections["south"]:
        boxes.append(rotate_box_y_cw(FENCE_ARM_LOW_NORTH, 2))
        boxes.append(rotate_box_y_cw(FENCE_ARM_HIGH_NORTH, 2))
    if connections["west"]:
        boxes.append(rotate_box_y_cw(FENCE_ARM_LOW_NORTH, 3))
        boxes.append(rotate_box_y_cw(FENCE_ARM_HIGH_NORTH, 3))

    return boxes