# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Callable, Iterable

from ..registry.block_registry import BlockRegistry
from .cardinal import normalize_cardinal
from ..state.state_codec import parse_state, format_state
from ..state.state_values import bool_str, str_as_bool
from .structural_rules import is_wall, is_fence_gate, wall_side_from_neighbor_state, wall_up_rule
from ..state.state_view import def_from_state, world_state_at
from ...world.world_state import WorldState

BlockKey = tuple[int, int, int]
GetState = Callable[[int, int, int], str | None]


def make_wall_state(base_id: str, waterlogged: bool=False) -> str:
    return format_state(str(base_id),{"east": "none", "north": "none", "south": "none", "up": "true", "waterlogged": bool_str(bool(waterlogged)), "west": "none"})


def _wall_side_from_neighbor(get_state: GetState, nb_x: int, nb_y: int, nb_z: int, *, side_from_neighbor: str, block_registry: BlockRegistry) -> str:
    st = get_state(int(nb_x), int(nb_y), int(nb_z))
    return wall_side_from_neighbor_state(st, side_from_neighbor=str(side_from_neighbor), get_def=block_registry.get)


def _gate_in_wall(get_state: GetState, x: int, y: int, z: int, facing: str, *, block_registry: BlockRegistry) -> bool:
    f = str(facing)
    if f in ("north", "south"):
        a = is_wall(def_from_state(get_state(int(x - 1), int(y), int(z)), block_registry))
        b = is_wall(def_from_state(get_state(int(x + 1), int(y), int(z)), block_registry))
        return bool(a or b)

    a = is_wall(def_from_state(get_state(int(x), int(y), int(z - 1)), block_registry))
    b = is_wall(def_from_state(get_state(int(x), int(y), int(z + 1)), block_registry))
    return bool(a or b)


def _canonical_wall_state(get_state: GetState, x: int, y: int, z: int, *, block_registry: BlockRegistry) -> str | None:
    st = get_state(int(x), int(y), int(z))
    d = def_from_state(st, block_registry)
    if st is None or (not is_wall(d)):
        return None

    base, props = parse_state(str(st))
    waterlogged = str_as_bool(props.get("waterlogged"), False)

    north = _wall_side_from_neighbor(get_state, int(x), int(y), int(z - 1), side_from_neighbor="south", block_registry=block_registry)
    east = _wall_side_from_neighbor(get_state, int(x + 1), int(y), int(z), side_from_neighbor="west", block_registry=block_registry)
    south = _wall_side_from_neighbor(get_state, int(x), int(y), int(z + 1), side_from_neighbor="north", block_registry=block_registry)
    west = _wall_side_from_neighbor(get_state, int(x - 1), int(y), int(z), side_from_neighbor="east", block_registry=block_registry)

    above_state = get_state(int(x), int(y + 1), int(z))
    up = wall_up_rule(north=str(north), east=str(east), south=str(south), west=str(west), above_state=above_state, get_def=block_registry.get)

    return format_state(str(base),{"east": str(east), "north": str(north), "south": str(south), "up": bool_str(bool(up)), "waterlogged": bool_str(bool(waterlogged)), "west": str(west)})


def make_fence_gate_state(base_id: str, facing: str, *, open_state: bool=False, powered: bool=False, in_wall: bool=False, waterlogged: bool=False) -> str:
    return format_state(str(base_id),{"facing": str(facing), "in_wall": bool_str(bool(in_wall)), "open": bool_str(bool(open_state)), "powered": bool_str(bool(powered)), "waterlogged": bool_str(bool(waterlogged))})


def _canonical_fence_gate_state(get_state: GetState, x: int, y: int, z: int, *, block_registry: BlockRegistry, facing_override: str | None=None, open_override: bool | None=None) -> str | None:
    st = get_state(int(x), int(y), int(z))
    d = def_from_state(st, block_registry)
    if st is None or (not is_fence_gate(d)):
        return None

    base, props = parse_state(str(st))

    if facing_override is not None:
        facing = normalize_cardinal(str(facing_override), default="south")
    else:
        facing = normalize_cardinal(str(props.get("facing", "south")), default="south")

    open_state = bool(open_override) if open_override is not None else str_as_bool(props.get("open"), False)
    powered = str_as_bool(props.get("powered"), False)
    waterlogged = str_as_bool(props.get("waterlogged"), False)
    in_wall = _gate_in_wall(get_state, int(x), int(y), int(z), str(facing), block_registry=block_registry)

    return make_fence_gate_state(str(base), str(facing), open_state=bool(open_state), powered=bool(powered), in_wall=bool(in_wall), waterlogged=bool(waterlogged))


def canonical_wall_state(world: WorldState, x: int, y: int, z: int, *, block_registry: BlockRegistry) -> str | None:
    return _canonical_wall_state(lambda gx, gy, gz: world_state_at(world, gx, gy, gz), int(x), int(y), int(z), block_registry=block_registry)


def canonical_fence_gate_state(world: WorldState, x: int, y: int, z: int, *, block_registry: BlockRegistry, facing_override: str | None=None, open_override: bool | None=None) -> str | None:
    return _canonical_fence_gate_state(lambda gx, gy, gz: world_state_at(world, gx, gy, gz), int(x), int(y), int(z), block_registry=block_registry, facing_override=facing_override, open_override=open_override)


def structural_neighbor_targets(cells: Iterable[BlockKey]) -> set[BlockKey]:
    targets: set[BlockKey] = set()
    for x0, y0, z0 in cells:
        x = int(x0)
        y = int(y0)
        z = int(z0)
        targets.add((int(x), int(y), int(z)))
        targets.add((int(x), int(y - 1), int(z)))
        targets.add((int(x + 1), int(y), int(z)))
        targets.add((int(x - 1), int(y), int(z)))
        targets.add((int(x), int(y), int(z + 1)))
        targets.add((int(x), int(y), int(z - 1)))
    return targets


def _overlay_state_getter(world: WorldState, *, overlay_updates: dict[BlockKey, str] | None=None, overlay_removals: Iterable[BlockKey]=()) -> GetState:
    updates = {(int(k[0]), int(k[1]), int(k[2])): str(v) for k, v in (overlay_updates or {}).items()}
    removals = {(int(k[0]), int(k[1]), int(k[2])) for k in overlay_removals}

    def get_state(x: int, y: int, z: int) -> str | None:
        key = (int(x), int(y), int(z))
        if key in removals:
            return None
        if key in updates:
            return str(updates[key])
        return world_state_at(world, int(x), int(y), int(z))

    return get_state


def collect_structural_neighbor_updates(world: WorldState, cells: Iterable[BlockKey], *, block_registry: BlockRegistry, overlay_updates: dict[BlockKey, str] | None=None, overlay_removals: Iterable[BlockKey]=()) -> dict[BlockKey, str]:
    get_state = _overlay_state_getter(world, overlay_updates=overlay_updates, overlay_removals=overlay_removals)
    updates: dict[BlockKey, str] = {}

    for tx, ty, tz in structural_neighbor_targets(cells):
        current_state = get_state(int(tx), int(ty), int(tz))
        d = def_from_state(current_state, block_registry)
        if current_state is None or d is None:
            continue

        nxt: str | None = None
        if is_wall(d):
            nxt = _canonical_wall_state(get_state, int(tx), int(ty), int(tz), block_registry=block_registry)
        elif is_fence_gate(d):
            nxt = _canonical_fence_gate_state(get_state, int(tx), int(ty), int(tz), block_registry=block_registry)

        if nxt is not None and str(nxt) != str(current_state):
            updates[(int(tx), int(ty), int(tz))] = str(nxt)

    return updates


def refresh_structural_neighbors(world: WorldState, x: int, y: int, z: int, *, block_registry: BlockRegistry) -> None:
    updates = collect_structural_neighbor_updates(world,((int(x), int(y), int(z)),), block_registry=block_registry)
    if updates:
        world.set_blocks_bulk(updates=updates)
