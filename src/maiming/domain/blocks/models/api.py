# FILE: src/maiming/domain/blocks/models/api.py
from __future__ import annotations

from typing import List

from maiming.domain.blocks.state_codec import parse_state
from maiming.domain.blocks.state_values import prop_as_bool
from maiming.domain.blocks.models.common import LocalBox, GetState, GetDef
from maiming.domain.blocks.models.slab import boxes_for_slab
from maiming.domain.blocks.models.stairs import boxes_for_stairs
from maiming.domain.blocks.models.fence import boxes_for_fence
from maiming.domain.blocks.models.fence_gate import boxes_for_fence_gate
from maiming.domain.blocks.models.wall import boxes_for_wall

_TALL_STRUCTURAL_MIN_HEIGHT = 1.5

def _raise_boxes_to_min_height(boxes: list[LocalBox], min_height: float) -> list[LocalBox]:
    out: list[LocalBox] = []
    h = float(min_height)

    for b in boxes:
        out.append(
            LocalBox(
                float(b.mn_x),
                float(b.mn_y),
                float(b.mn_z),
                float(b.mx_x),
                max(float(h), float(b.mx_y)),
                float(b.mx_z),
                uv_hint=str(b.uv_hint),
            )
        )

    return out

def _gate_interact_hull(props: dict[str, str]) -> LocalBox:
    """
    The fence-gate interaction volume is intentionally decoupled from both the
    rendered bars and the closed-state collision barrier. The prior full-block
    hull solved usability at the cost of semantic corruption: right-click rays
    were captured by an artificial one-block-thick slab of space, so the user
    could target regions that are visually and mechanically too distant from the
    actual gate plane. The correct engineering compromise is to preserve the
    actionable central opening while constraining capture thickness to a narrow
    planar band aligned with the gate's own axis.

    The hull therefore spans the central aperture in width and the practical
    interaction height of the gate, yet remains thin along the gate plane. This
    retains the required behavior that the gate reacts when the player aims at
    the central air region, including the opened state, while preventing the
    exaggerated front/back reach introduced by the previous 1×1×1.5 proxy.
    """
    facing = str(props.get("facing", "south"))

    if facing in ("north", "south"):
        return LocalBox(
            mn_x=2.0 / 16.0,
            mn_y=0.0,
            mn_z=6.0 / 16.0,
            mx_x=14.0 / 16.0,
            mx_y=24.0 / 16.0,
            mx_z=10.0 / 16.0,
            uv_hint="interact",
        )

    return LocalBox(
        mn_x=6.0 / 16.0,
        mn_y=0.0,
        mn_z=2.0 / 16.0,
        mx_x=10.0 / 16.0,
        mx_y=24.0 / 16.0,
        mx_z=14.0 / 16.0,
        uv_hint="interact",
    )

def render_boxes_for_block(
    state_str: str,
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    base, props = parse_state(state_str)
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"

    if kind == "slab":
        return boxes_for_slab(props)

    if kind == "stairs":
        return boxes_for_stairs(
            base_id=str(base),
            props=props,
            get_state=get_state,
            get_def=get_def,
            x=int(x),
            y=int(y),
            z=int(z),
        )

    if kind == "fence":
        return boxes_for_fence(get_state=get_state, get_def=get_def, x=int(x), y=int(y), z=int(z))

    if kind == "fence_gate":
        return boxes_for_fence_gate(props)

    if kind == "wall":
        return boxes_for_wall(
            props=props,
            get_state=get_state,
            get_def=get_def,
            x=int(x),
            y=int(y),
            z=int(z),
        )

    if kind == "short_cube":
        return [LocalBox(0.0, 0.0, 0.0, 1.0, 15.0 / 16.0, 1.0)]

    return [LocalBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)]

def _tall_structural_boxes(
    state_str: str,
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    return _raise_boxes_to_min_height(
        render_boxes_for_block(state_str, get_state, get_def, x, y, z),
        _TALL_STRUCTURAL_MIN_HEIGHT,
    )

def _fence_gate_pick_boxes(
    state_str: str,
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    _base, props = parse_state(state_str)

    if prop_as_bool(props, "open", False):
        out = list(render_boxes_for_block(state_str, get_state, get_def, x, y, z))
    else:
        out = list(_tall_structural_boxes(state_str, get_state, get_def, x, y, z))

    out.append(_gate_interact_hull(props))
    return out

def collision_boxes_for_block(
    state_str: str,
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    base, props = parse_state(state_str)
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"

    if kind == "fence_gate":
        if prop_as_bool(props, "open", False):
            return []
        return _tall_structural_boxes(state_str, get_state, get_def, x, y, z)

    if kind in ("fence", "wall"):
        return _tall_structural_boxes(state_str, get_state, get_def, x, y, z)

    return render_boxes_for_block(state_str, get_state, get_def, x, y, z)

def pick_boxes_for_block(
    state_str: str,
    get_state: GetState,
    get_def: GetDef,
    x: int,
    y: int,
    z: int,
) -> List[LocalBox]:
    base, _props = parse_state(state_str)
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"

    if kind == "fence_gate":
        return _fence_gate_pick_boxes(state_str, get_state, get_def, x, y, z)

    if kind in ("fence", "wall"):
        return _tall_structural_boxes(state_str, get_state, get_def, x, y, z)

    return render_boxes_for_block(state_str, get_state, get_def, x, y, z)