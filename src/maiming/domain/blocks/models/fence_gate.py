# FILE: src/maiming/domain/blocks/models/fence_gate.py
from __future__ import annotations

from typing import Dict, List

from maiming.domain.blocks.models.common import LocalBox, rotate_box_y_cw, gate_turns_from_facing
from maiming.domain.blocks.models.dimensions import (
    FENCE_GATE_CLOSED,
    FENCE_GATE_OPEN,
    FENCE_GATE_WALL_CLOSED,
    FENCE_GATE_WALL_OPEN,
)

def boxes_for_fence_gate(props: Dict[str, str]) -> List[LocalBox]:
    facing = str(props.get("facing", "south"))

    open_s = str(props.get("open", "false")).lower()
    is_open = open_s in ("1", "true", "yes", "on")

    in_wall_s = str(props.get("in_wall", "false")).lower()
    in_wall = in_wall_s in ("1", "true", "yes", "on")

    if bool(is_open):
        src = FENCE_GATE_WALL_OPEN if bool(in_wall) else FENCE_GATE_OPEN
    else:
        src = FENCE_GATE_WALL_CLOSED if bool(in_wall) else FENCE_GATE_CLOSED

    turns = gate_turns_from_facing(facing)
    return [rotate_box_y_cw(b, turns) for b in src]