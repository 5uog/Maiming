# FILE: src/maiming/domain/blocks/models/api.py
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
from typing import Sequence

from ....core.geometry.aabb import AABB
from ....core.math.vec3 import Vec3

from ..neighborhood import six_neighbor_state_signature
from ..state_codec import parse_state
from ..state_values import prop_as_bool

from .common import LocalBox, GetState, GetDef
from .slab import boxes_for_slab
from .stairs import boxes_for_stairs
from .fence import boxes_for_fence
from .fence_gate import boxes_for_fence_gate
from .wall import boxes_for_wall

_TALL_STRUCTURAL_MIN_HEIGHT = 1.5
_LOCAL_BOX_CACHE_CAP = 32768
_WORLD_AABB_CACHE_CAP = 32768

class _TupleLruCache:
    def __init__(self, max_entries: int) -> None:
        self._max_entries = int(max(1, int(max_entries)))
        self._lock = RLock()
        self._data: OrderedDict[tuple[object, ...], tuple[object, ...]] = OrderedDict()

    def get(self, key: tuple[object, ...]) -> tuple[object, ...] | None:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            self._data.move_to_end(key)
            return hit

    def set(self, key: tuple[object, ...], value: tuple[object, ...]) -> tuple[object, ...]:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._max_entries:
                self._data.popitem(last=False)
            return value

_RENDER_BOX_CACHE = _TupleLruCache(_LOCAL_BOX_CACHE_CAP)
_COLLISION_BOX_CACHE = _TupleLruCache(_LOCAL_BOX_CACHE_CAP)
_PICK_BOX_CACHE = _TupleLruCache(_LOCAL_BOX_CACHE_CAP)

_COLLISION_AABB_CACHE = _TupleLruCache(_WORLD_AABB_CACHE_CAP)
_PICK_AABB_CACHE = _TupleLruCache(_WORLD_AABB_CACHE_CAP)

def _callable_cache_token(fn: object) -> int:
    owner = getattr(fn, "__self__", None)
    if owner is not None:
        return int(id(owner))
    return int(id(fn))

def _shape_signature(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[object, ...]:
    return (int(_callable_cache_token(get_def)), str(state_str), *six_neighbor_state_signature(get_state, int(x), int(y), int(z)))

def _raise_boxes_to_min_height(boxes: Sequence[LocalBox], min_height: float) -> tuple[LocalBox, ...]:
    out: list[LocalBox] = []
    h = float(min_height)

    for b in boxes:
        out.append(LocalBox(float(b.mn_x), float(b.mn_y), float(b.mn_z), float(b.mx_x), max(float(h), float(b.mx_y)), float(b.mx_z), uv_hint=str(b.uv_hint)))

    return tuple(out)

def _gate_interact_hull(props: dict[str, str]) -> LocalBox:
    facing = str(props.get("facing", "south"))

    if facing in ("north", "south"):
        return LocalBox(mn_x=2.0 / 16.0, mn_y=0.0, mn_z=6.0 / 16.0, mx_x=14.0 / 16.0, mx_y=24.0 / 16.0, mx_z=10.0 / 16.0, uv_hint="interact")

    return LocalBox(mn_x=6.0 / 16.0, mn_y=0.0, mn_z=2.0 / 16.0, mx_x=10.0 / 16.0, mx_y=24.0 / 16.0, mx_z=14.0 / 16.0, uv_hint="interact")

def _render_boxes_uncached(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[LocalBox, ...]:
    base, props = parse_state(state_str)
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"

    if kind == "slab":
        return tuple(boxes_for_slab(props))

    if kind == "stairs":
        return tuple(boxes_for_stairs(base_id=str(base), props=props, get_state=get_state, get_def=get_def, x=int(x), y=int(y), z=int(z)))

    if kind == "fence":
        return tuple(boxes_for_fence(get_state=get_state, get_def=get_def, x=int(x), y=int(y), z=int(z)))

    if kind == "fence_gate":
        return tuple(boxes_for_fence_gate(props))

    if kind == "wall":
        return tuple(boxes_for_wall(props=props, get_state=get_state, get_def=get_def, x=int(x), y=int(y), z=int(z)))

    if kind == "short_cube":
        return (LocalBox(0.0, 0.0, 0.0, 1.0, 15.0 / 16.0, 1.0),)

    return (LocalBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0),)

def render_boxes_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[LocalBox]:
    key = _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))
    cached = _RENDER_BOX_CACHE.get(key)
    if cached is not None:
        return cached

    boxes = _render_boxes_uncached(str(state_str), get_state, get_def, int(x), int(y), int(z))
    return _RENDER_BOX_CACHE.set(key, boxes)

def _tall_structural_boxes(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[LocalBox, ...]:
    return _raise_boxes_to_min_height(render_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)), _TALL_STRUCTURAL_MIN_HEIGHT)

def _fence_gate_pick_boxes(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[LocalBox, ...]:
    _base, props = parse_state(str(state_str))

    if prop_as_bool(props, "open", False):
        out = list(render_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)))
    else:
        out = list(_tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z)))

    out.append(_gate_interact_hull(props))
    return tuple(out)

def collision_boxes_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[LocalBox]:
    key = ("collision",) + _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))
    cached = _COLLISION_BOX_CACHE.get(key)
    if cached is not None:
        return cached

    base, props = parse_state(str(state_str))
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"

    if kind == "fence_gate":
        if prop_as_bool(props, "open", False):
            boxes: tuple[LocalBox, ...] = ()
        else:
            boxes = _tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))
        return _COLLISION_BOX_CACHE.set(key, boxes)

    if kind in ("fence", "wall"):
        boxes = _tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))
        return _COLLISION_BOX_CACHE.set(key, boxes)

    boxes = tuple(render_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)))
    return _COLLISION_BOX_CACHE.set(key, boxes)

def pick_boxes_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[LocalBox]:
    key = ("pick",) + _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))
    cached = _PICK_BOX_CACHE.get(key)
    if cached is not None:
        return cached

    base, _props = parse_state(str(state_str))
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"

    if kind == "fence_gate":
        boxes = _fence_gate_pick_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))
        return _PICK_BOX_CACHE.set(key, boxes)

    if kind in ("fence", "wall"):
        boxes = _tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))
        return _PICK_BOX_CACHE.set(key, boxes)

    boxes = tuple(render_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)))
    return _PICK_BOX_CACHE.set(key, boxes)

def _translate_boxes_to_aabbs(boxes: Sequence[LocalBox], x: int, y: int, z: int) -> tuple[AABB, ...]:
    px = int(x)
    py = int(y)
    pz = int(z)

    out: list[AABB] = []
    for b in boxes:
        out.append(AABB(mn=Vec3(float(px) + float(b.mn_x), float(py) + float(b.mn_y), float(pz) + float(b.mn_z)), mx=Vec3(float(px) + float(b.mx_x), float(py) + float(b.mx_y), float(pz) + float(b.mx_z))))
    return tuple(out)

def collision_aabbs_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[AABB]:
    key = ("collision_aabb", int(x), int(y), int(z)) + _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))
    cached = _COLLISION_AABB_CACHE.get(key)
    if cached is not None:
        return cached

    aabbs = _translate_boxes_to_aabbs(collision_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)), int(x), int(y), int(z))
    return _COLLISION_AABB_CACHE.set(key, aabbs)

def pick_aabbs_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[AABB]:
    key = ("pick_aabb", int(x), int(y), int(z)) + _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))
    cached = _PICK_AABB_CACHE.get(key)
    if cached is not None:
        return cached

    aabbs = _translate_boxes_to_aabbs(pick_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)), int(x), int(y), int(z))
    return _PICK_AABB_CACHE.set(key, aabbs)