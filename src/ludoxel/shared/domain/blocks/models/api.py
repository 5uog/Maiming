# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
from typing import Sequence

from ....core.spatial.geometry.aabb import AABB
from ....core.math.vec3 import Vec3

from ..structure.cardinal import normalize_cardinal
from ..structure.neighborhood import six_neighbor_state_signature
from ..state.state_codec import parse_state
from ..state.state_values import prop_as_bool

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

def _local_box_cache_key(namespace: str, state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[object, ...]:
    return (str(namespace),) + _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))

def _world_aabb_cache_key(namespace: str, state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[object, ...]:
    return (str(namespace), int(x), int(y), int(z)) + _shape_signature(str(state_str), get_state, get_def, int(x), int(y), int(z))

def _cache_get_or_build(cache: _TupleLruCache, key: tuple[object, ...], builder) -> tuple[object, ...]:
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = builder()
    return cache.set(key, value)

def _resolve_block_kind(state_str: str, get_def: GetDef) -> tuple[str, dict[str, str], str]:
    base, props = parse_state(str(state_str))
    defn = get_def(str(base))
    kind = defn.kind if defn is not None else "cube"
    return (str(base), props, str(kind))

def _raise_boxes_to_min_height(boxes: Sequence[LocalBox], min_height: float) -> tuple[LocalBox, ...]:
    out: list[LocalBox] = []
    h = float(min_height)

    for b in boxes:
        out.append(LocalBox(float(b.mn_x), float(b.mn_y), float(b.mn_z), float(b.mx_x), max(float(h), float(b.mx_y)), float(b.mx_z), uv_hint=str(b.uv_hint)))

    return tuple(out)

def _gate_interact_hull(props: dict[str, str]) -> LocalBox:
    facing = normalize_cardinal(str(props.get("facing", "south")), default="south")

    if facing in ("north", "south"):
        return LocalBox(mn_x=2.0 / 16.0, mn_y=0.0, mn_z=6.0 / 16.0, mx_x=14.0 / 16.0, mx_y=24.0 / 16.0, mx_z=10.0 / 16.0, uv_hint="interact")

    return LocalBox(mn_x=6.0 / 16.0, mn_y=0.0, mn_z=2.0 / 16.0, mx_x=10.0 / 16.0, mx_y=24.0 / 16.0, mx_z=14.0 / 16.0, uv_hint="interact")

def _render_boxes_uncached(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> tuple[LocalBox, ...]:
    base, props, kind = _resolve_block_kind(str(state_str), get_def)

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
    key = _local_box_cache_key("render", str(state_str), get_state, get_def, int(x), int(y), int(z))
    return _cache_get_or_build(_RENDER_BOX_CACHE, key, lambda: _render_boxes_uncached(str(state_str), get_state, get_def, int(x), int(y), int(z)))

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
    key = _local_box_cache_key("collision", str(state_str), get_state, get_def, int(x), int(y), int(z))

    def _build() -> tuple[LocalBox, ...]:
        _base, props, kind = _resolve_block_kind(str(state_str), get_def)

        if kind == "fence_gate":
            if prop_as_bool(props, "open", False):
                return ()
            return _tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))

        if kind in ("fence", "wall"):
            return _tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))

        return tuple(render_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)))

    return _cache_get_or_build(_COLLISION_BOX_CACHE, key, _build)

def pick_boxes_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[LocalBox]:
    key = _local_box_cache_key("pick", str(state_str), get_state, get_def, int(x), int(y), int(z))

    def _build() -> tuple[LocalBox, ...]:
        _base, _props, kind = _resolve_block_kind(str(state_str), get_def)

        if kind == "fence_gate":
            return _fence_gate_pick_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))

        if kind in ("fence", "wall"):
            return _tall_structural_boxes(str(state_str), get_state, get_def, int(x), int(y), int(z))

        return tuple(render_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)))

    return _cache_get_or_build(_PICK_BOX_CACHE, key, _build)

def _translate_boxes_to_aabbs(boxes: Sequence[LocalBox], x: int, y: int, z: int) -> tuple[AABB, ...]:
    px = int(x)
    py = int(y)
    pz = int(z)

    out: list[AABB] = []
    for b in boxes:
        out.append(AABB(mn=Vec3(float(px) + float(b.mn_x), float(py) + float(b.mn_y), float(pz) + float(b.mn_z)), mx=Vec3(float(px) + float(b.mx_x), float(py) + float(b.mx_y), float(pz) + float(b.mx_z))))
    return tuple(out)

def collision_aabbs_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[AABB]:
    key = _world_aabb_cache_key("collision_aabb", str(state_str), get_state, get_def, int(x), int(y), int(z))
    return _cache_get_or_build(_COLLISION_AABB_CACHE, key, lambda: _translate_boxes_to_aabbs(collision_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)), int(x), int(y), int(z)))

def pick_aabbs_for_block(state_str: str, get_state: GetState, get_def: GetDef, x: int, y: int, z: int) -> Sequence[AABB]:
    key = _world_aabb_cache_key("pick_aabb", str(state_str), get_state, get_def, int(x), int(y), int(z))
    return _cache_get_or_build(_PICK_AABB_CACHE, key, lambda: _translate_boxes_to_aabbs(pick_boxes_for_block(str(state_str), get_state, get_def, int(x), int(y), int(z)), int(x), int(y), int(z)))