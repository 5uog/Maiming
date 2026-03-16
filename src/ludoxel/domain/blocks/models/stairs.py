# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/models/stairs.py
from __future__ import annotations

from typing import Dict, List

from ..state_codec import parse_state
from .common import LocalBox, GetState, GetDef, rotate_box_y_cw
from ..cardinal import cardinal_turns_from_facing
from ..structural_rules import is_stairs


def _stairs_shape(props: Dict[str, str], get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> str:
    facing = str(props.get("facing", "east"))
    if facing not in ("north", "east", "south", "west"):
        facing = "east"

    half = str(props.get("half", "bottom"))
    if half not in ("bottom", "top"):
        half = "bottom"

    def _is_connectable_stair_at(nx: int, ny: int, nz: int) -> tuple[bool, str]:
        s = get_state(nx, ny, nz)
        if s is None:
            return (False, "east")

        b, p = parse_state(s)
        d = get_def(str(b))
        if d is None or (not is_stairs(d)):
            return (False, "east")

        nh = str(p.get("half", "bottom"))
        if nh not in ("bottom", "top"):
            nh = "bottom"
        if nh != half:
            return (False, "east")

        nf = str(p.get("facing", "east"))
        if nf not in ("north", "east", "south", "west"):
            nf = "east"

        return (True, nf)

    dir_vec: dict[str, tuple[int, int]] = {"east": (1, 0), "south": (0, 1), "west": (-1, 0), "north": (0, -1)}
    left = {"east": "north", "north": "west", "west": "south", "south": "east"}[facing]
    right = {"east": "south", "south": "west", "west": "north", "north": "east"}[facing]

    fdx, fdz = dir_vec[facing]

    ok_f, fc_f = _is_connectable_stair_at(x + fdx, y, z + fdz)
    if ok_f:
        if fc_f == left:
            return "outer_left"
        if fc_f == right:
            return "outer_right"

    ok_b, fc_b = _is_connectable_stair_at(x - fdx, y, z - fdz)
    if ok_b:
        if fc_b == left:
            return "inner_left"
        if fc_b == right:
            return "inner_right"

    return "straight"


def boxes_for_stairs(*, base_id: str, props: Dict[str, str], get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> List[LocalBox]:
    _ = base_id

    facing = str(props.get("facing", "east"))
    half = str(props.get("half", "bottom"))
    if half not in ("bottom", "top"):
        half = "bottom"

    shape = _stairs_shape(props, get_state, get_def, int(x), int(y), int(z))

    if half == "bottom":
        base_y0, base_y1 = 0.0, 0.5
        step_y0, step_y1 = 0.5, 1.0
    else:
        base_y0, base_y1 = 0.5, 1.0
        step_y0, step_y1 = 0.0, 0.5

    def base_q(x0: float, x1: float, z0: float, z1: float) -> LocalBox:
        return LocalBox(float(x0), float(base_y0), float(z0), float(x1), float(base_y1), float(z1))

    base_boxes: list[LocalBox] = [base_q(0.0, 0.5, 0.0, 0.5), base_q(0.5, 1.0, 0.0, 0.5), base_q(0.0, 0.5, 0.5, 1.0), base_q(0.5, 1.0, 0.5, 1.0)]

    def step_box(x0: float, x1: float, z0: float, z1: float) -> LocalBox:
        return LocalBox(float(x0), float(step_y0), float(z0), float(x1), float(step_y1), float(z1))

    step_boxes: list[LocalBox] = []
    if shape == "straight":
        step_boxes.append(step_box(0.5, 1.0, 0.0, 1.0))
    elif shape == "outer_left":
        step_boxes.append(step_box(0.5, 1.0, 0.0, 0.5))
    elif shape == "outer_right":
        step_boxes.append(step_box(0.5, 1.0, 0.5, 1.0))
    elif shape == "inner_left":
        step_boxes.append(step_box(0.5, 1.0, 0.0, 1.0))
        step_boxes.append(step_box(0.0, 0.5, 0.0, 0.5))
    elif shape == "inner_right":
        step_boxes.append(step_box(0.5, 1.0, 0.0, 1.0))
        step_boxes.append(step_box(0.0, 0.5, 0.5, 1.0))
    else:
        step_boxes.append(step_box(0.5, 1.0, 0.0, 1.0))

    turns = cardinal_turns_from_facing(facing)
    boxes = base_boxes + step_boxes
    return [rotate_box_y_cw(b, turns) for b in boxes]
