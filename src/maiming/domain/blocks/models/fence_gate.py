# FILE: src/maiming/domain/blocks/models/fence_gate.py
from __future__ import annotations

from typing import Dict, List

from maiming.domain.blocks.models.common import LocalBox, rotate_box_y_cw, gate_turns_from_facing

def boxes_for_fence_gate(props: Dict[str, str]) -> List[LocalBox]:
    facing = str(props.get("facing", "south"))
    open_s = str(props.get("open", "false")).lower()
    is_open = open_s in ("1", "true", "yes", "on")

    closed_boxes = [
        LocalBox(0.0 / 16.0, 5.0 / 16.0, 7.0 / 16.0, 2.0 / 16.0, 16.0 / 16.0, 9.0 / 16.0),
        LocalBox(14.0 / 16.0, 5.0 / 16.0, 7.0 / 16.0, 16.0 / 16.0, 16.0 / 16.0, 9.0 / 16.0),
        LocalBox(6.0 / 16.0, 6.0 / 16.0, 7.0 / 16.0, 8.0 / 16.0, 15.0 / 16.0, 9.0 / 16.0),
        LocalBox(8.0 / 16.0, 6.0 / 16.0, 7.0 / 16.0, 10.0 / 16.0, 15.0 / 16.0, 9.0 / 16.0),
        LocalBox(2.0 / 16.0, 6.0 / 16.0, 7.0 / 16.0, 6.0 / 16.0, 9.0 / 16.0, 9.0 / 16.0),
        LocalBox(2.0 / 16.0, 12.0 / 16.0, 7.0 / 16.0, 6.0 / 16.0, 15.0 / 16.0, 9.0 / 16.0),
        LocalBox(10.0 / 16.0, 6.0 / 16.0, 7.0 / 16.0, 14.0 / 16.0, 9.0 / 16.0, 9.0 / 16.0),
        LocalBox(10.0 / 16.0, 12.0 / 16.0, 7.0 / 16.0, 14.0 / 16.0, 15.0 / 16.0, 9.0 / 16.0),
    ]

    open_boxes = [
        LocalBox(0.0 / 16.0, 5.0 / 16.0, 7.0 / 16.0, 2.0 / 16.0, 16.0 / 16.0, 9.0 / 16.0),
        LocalBox(14.0 / 16.0, 5.0 / 16.0, 7.0 / 16.0, 16.0 / 16.0, 16.0 / 16.0, 9.0 / 16.0),
        LocalBox(0.0 / 16.0, 6.0 / 16.0, 13.0 / 16.0, 2.0 / 16.0, 15.0 / 16.0, 15.0 / 16.0),
        LocalBox(14.0 / 16.0, 6.0 / 16.0, 13.0 / 16.0, 16.0 / 16.0, 15.0 / 16.0, 15.0 / 16.0),
        LocalBox(0.0 / 16.0, 6.0 / 16.0, 9.0 / 16.0, 2.0 / 16.0, 9.0 / 16.0, 13.0 / 16.0),
        LocalBox(0.0 / 16.0, 12.0 / 16.0, 9.0 / 16.0, 2.0 / 16.0, 15.0 / 16.0, 13.0 / 16.0),
        LocalBox(14.0 / 16.0, 6.0 / 16.0, 9.0 / 16.0, 16.0 / 16.0, 9.0 / 16.0, 13.0 / 16.0),
        LocalBox(14.0 / 16.0, 12.0 / 16.0, 9.0 / 16.0, 16.0 / 16.0, 15.0 / 16.0, 13.0 / 16.0),
    ]

    turns = gate_turns_from_facing(facing)
    src = open_boxes if is_open else closed_boxes
    return [rotate_box_y_cw(b, turns) for b in src]