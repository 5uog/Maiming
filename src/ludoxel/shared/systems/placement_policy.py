# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
import math

from ..math.vec3 import Vec3
from ..world.entities.player_entity import PlayerEntity
from ..world.world_state import WorldState
from ..blocks.registry.block_registry import BlockRegistry
from ..blocks.structure.cardinal import cardinal_from_xz
from ..blocks.structure.connectivity import make_fence_gate_state, make_wall_state
from ..blocks.models.api import collision_aabbs_for_block
from ..blocks.state.state_codec import format_state, parse_state
from ..blocks.state.state_values import slab_type_value
from ..blocks.structure.structural_rules import is_fence_gate, is_slab, is_stairs, is_wall


@dataclass(frozen=True)
class PlacementPolicy:
    block_registry: BlockRegistry

    def _player_cardinal(self, player: PlayerEntity) -> str:
        f = player.view_forward()
        return cardinal_from_xz(float(f.x), float(f.z), default="south")

    @staticmethod
    def _choose_half_type(hit_face: int, hit_point: Vec3) -> str:
        if int(hit_face) == 2:
            return "bottom"
        if int(hit_face) == 3:
            return "top"

        base_y = math.floor(float(hit_point.y))
        fy = float(hit_point.y) - float(base_y)
        fy = max(0.0, min(1.0, float(fy)))
        return "top" if fy >= 0.5 else "bottom"

    def _try_merge_same_slab(self, *, existing_state: str, block_id: str, desired_type: str) -> str | None:
        base, props = parse_state(str(existing_state))
        if str(base) != str(block_id):
            return None

        defn = self.block_registry.get(str(base))
        if defn is None or (not is_slab(defn)):
            return None

        want = str(desired_type)
        if want not in ("bottom", "top"):
            return None

        cur = slab_type_value(props)
        if cur == "double" or cur == want:
            return None

        return format_state(str(base),{"type": "double"})

    def resolve_slab_merge_state(self, *, existing_state: str, block_id: str, hit_face: int, hit_point: Vec3) -> str | None:
        desired_type = self._choose_half_type(int(hit_face), hit_point)
        return self._try_merge_same_slab(existing_state=str(existing_state), block_id=str(block_id), desired_type=str(desired_type))

    def resolve_slab_merge_state_from_hit(self, *, existing_state: str, block_id: str, hit_face: int) -> str | None:
        face = int(hit_face)

        if face == 2:
            desired_type = "top"
        elif face == 3:
            desired_type = "bottom"
        else:
            return None

        return self._try_merge_same_slab(existing_state=str(existing_state), block_id=str(block_id), desired_type=str(desired_type))

    def resolve_place_state(self, *, player: PlayerEntity, block_id: str, hit_face: int, hit_point: Vec3) -> str | None:
        base_sel = str(block_id)
        defn = self.block_registry.get(base_sel)
        if defn is None:
            return None

        props: dict[str, str] = {}

        if is_slab(defn):
            props["type"] = self._choose_half_type(int(hit_face), hit_point)
            return format_state(base_sel, props)

        if is_stairs(defn):
            props["facing"] = self._player_cardinal(player)
            props["half"] = self._choose_half_type(int(hit_face), hit_point)
            return format_state(base_sel, props)

        if is_fence_gate(defn):
            return make_fence_gate_state(base_sel, self._player_cardinal(player), open_state=False)

        if is_wall(defn):
            return make_wall_state(base_sel, waterlogged=False)

        return format_state(base_sel, props)

    def placement_intersects_player(self, *, player: PlayerEntity, world: WorldState, px: int, py: int, pz: int, place_state: str) -> bool:
        pa = player.aabb_at(player.position)

        def get_state(x: int, y: int, z: int) -> str | None:
            k = (int(x), int(y), int(z))
            if k == (int(px), int(py), int(pz)):
                return str(place_state)
            return world.blocks.get(k)

        for ba in collision_aabbs_for_block(str(place_state), get_state, self.block_registry.get, int(px), int(py), int(pz)):
            if pa.intersects(ba):
                return True

        return False
