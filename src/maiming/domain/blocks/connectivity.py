# FILE: src/maiming/domain/blocks/connectivity.py
from __future__ import annotations

from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.state_codec import parse_state, format_state
from maiming.domain.blocks.structural_rules import (
    is_wall,
    is_fence_gate,
    wall_side_from_neighbor_state,
    wall_up_rule,
)
from maiming.domain.world.world_state import WorldState

def _bool_str(v: bool) -> str:
    return "true" if bool(v) else "false"

def _as_bool(s: str | None, default: bool = False) -> bool:
    if s is None:
        return bool(default)
    t = str(s).strip().lower()
    if t in ("1", "true", "yes", "on"):
        return True
    if t in ("0", "false", "no", "off"):
        return False
    return bool(default)

def _state_at(world: WorldState, x: int, y: int, z: int) -> str | None:
    return world.blocks.get((int(x), int(y), int(z)))

def _def_from_state(state_str: str | None, block_registry: BlockRegistry) -> BlockDefinition | None:
    if state_str is None:
        return None
    base, _props = parse_state(str(state_str))
    return block_registry.get(str(base))

def make_wall_state(base_id: str, waterlogged: bool = False) -> str:
    return format_state(
        str(base_id),
        {
            "east": "none",
            "north": "none",
            "south": "none",
            "up": "true",
            "waterlogged": _bool_str(bool(waterlogged)),
            "west": "none",
        },
    )

def _wall_side_from_neighbor(
    world: WorldState,
    nb_x: int,
    nb_y: int,
    nb_z: int,
    *,
    side_from_neighbor: str,
    block_registry: BlockRegistry,
) -> str:
    st = _state_at(world, int(nb_x), int(nb_y), int(nb_z))
    return wall_side_from_neighbor_state(
        st,
        side_from_neighbor=str(side_from_neighbor),
        get_def=block_registry.get,
    )

def canonical_wall_state(
    world: WorldState,
    x: int,
    y: int,
    z: int,
    *,
    block_registry: BlockRegistry,
) -> str | None:
    st = _state_at(world, int(x), int(y), int(z))
    d = _def_from_state(st, block_registry)
    if st is None or (not is_wall(d)):
        return None

    base, props = parse_state(str(st))
    waterlogged = _as_bool(props.get("waterlogged"), False)

    north = _wall_side_from_neighbor(
        world,
        int(x),
        int(y),
        int(z - 1),
        side_from_neighbor="south",
        block_registry=block_registry,
    )
    east = _wall_side_from_neighbor(
        world,
        int(x + 1),
        int(y),
        int(z),
        side_from_neighbor="west",
        block_registry=block_registry,
    )
    south = _wall_side_from_neighbor(
        world,
        int(x),
        int(y),
        int(z + 1),
        side_from_neighbor="north",
        block_registry=block_registry,
    )
    west = _wall_side_from_neighbor(
        world,
        int(x - 1),
        int(y),
        int(z),
        side_from_neighbor="east",
        block_registry=block_registry,
    )

    above_def = _def_from_state(_state_at(world, int(x), int(y + 1), int(z)), block_registry)
    up = wall_up_rule(
        north=str(north),
        east=str(east),
        south=str(south),
        west=str(west),
        above_def=above_def,
    )

    return format_state(
        str(base),
        {
            "east": str(east),
            "north": str(north),
            "south": str(south),
            "up": _bool_str(bool(up)),
            "waterlogged": _bool_str(bool(waterlogged)),
            "west": str(west),
        },
    )

def make_fence_gate_state(
    base_id: str,
    facing: str,
    *,
    open_state: bool = False,
    powered: bool = False,
    in_wall: bool = False,
    waterlogged: bool = False,
) -> str:
    return format_state(
        str(base_id),
        {
            "facing": str(facing),
            "in_wall": _bool_str(bool(in_wall)),
            "open": _bool_str(bool(open_state)),
            "powered": _bool_str(bool(powered)),
            "waterlogged": _bool_str(bool(waterlogged)),
        },
    )

def _gate_in_wall(
    world: WorldState,
    x: int,
    y: int,
    z: int,
    facing: str,
    *,
    block_registry: BlockRegistry,
) -> bool:
    f = str(facing)
    if f in ("north", "south"):
        a = is_wall(_def_from_state(_state_at(world, int(x - 1), int(y), int(z)), block_registry))
        b = is_wall(_def_from_state(_state_at(world, int(x + 1), int(y), int(z)), block_registry))
        return bool(a or b)

    a = is_wall(_def_from_state(_state_at(world, int(x), int(y), int(z - 1)), block_registry))
    b = is_wall(_def_from_state(_state_at(world, int(x), int(y), int(z + 1)), block_registry))
    return bool(a or b)

def canonical_fence_gate_state(
    world: WorldState,
    x: int,
    y: int,
    z: int,
    *,
    block_registry: BlockRegistry,
    facing_override: str | None = None,
    open_override: bool | None = None,
) -> str | None:
    st = _state_at(world, int(x), int(y), int(z))
    d = _def_from_state(st, block_registry)
    if st is None or (not is_fence_gate(d)):
        return None

    base, props = parse_state(str(st))

    facing = str(facing_override) if facing_override is not None else str(props.get("facing", "south"))
    if facing not in ("north", "east", "south", "west"):
        facing = "south"

    open_state = bool(open_override) if open_override is not None else _as_bool(props.get("open"), False)
    powered = _as_bool(props.get("powered"), False)
    waterlogged = _as_bool(props.get("waterlogged"), False)
    in_wall = _gate_in_wall(
        world,
        int(x),
        int(y),
        int(z),
        str(facing),
        block_registry=block_registry,
    )

    return make_fence_gate_state(
        str(base),
        str(facing),
        open_state=bool(open_state),
        powered=bool(powered),
        in_wall=bool(in_wall),
        waterlogged=bool(waterlogged),
    )

def refresh_structural_neighbors(
    world: WorldState,
    x: int,
    y: int,
    z: int,
    *,
    block_registry: BlockRegistry,
) -> None:
    targets = {
        (int(x), int(y), int(z)),
        (int(x), int(y - 1), int(z)),
        (int(x + 1), int(y), int(z)),
        (int(x - 1), int(y), int(z)),
        (int(x), int(y), int(z + 1)),
        (int(x), int(y), int(z - 1)),
    }

    updates: list[tuple[int, int, int, str]] = []

    for tx, ty, tz in targets:
        st = _state_at(world, int(tx), int(ty), int(tz))
        d = _def_from_state(st, block_registry)
        if st is None or d is None:
            continue

        nxt: str | None = None
        if is_wall(d):
            nxt = canonical_wall_state(
                world,
                int(tx),
                int(ty),
                int(tz),
                block_registry=block_registry,
            )
        elif is_fence_gate(d):
            nxt = canonical_fence_gate_state(
                world,
                int(tx),
                int(ty),
                int(tz),
                block_registry=block_registry,
            )

        if nxt is not None and str(nxt) != str(st):
            updates.append((int(tx), int(ty), int(tz), str(nxt)))

    for tx, ty, tz, nxt in updates:
        world.set_block(int(tx), int(ty), int(tz), str(nxt))