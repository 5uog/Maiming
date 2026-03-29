# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field

from ..math.vec3 import Vec3
from ..world.world_state import WorldState
from ..world.entities.player_entity import PlayerEntity

from ..blocks.registry.block_registry import BlockRegistry
from ..blocks.state.state_codec import parse_state
from ..blocks.structure.cardinal import normalize_cardinal, opposite_cardinal, facing_vec_xz
from ..blocks.structure.connectivity import canonical_fence_gate_state, collect_structural_neighbor_updates, make_fence_gate_state
from ..blocks.structure.structural_rules import is_fence_gate
from ..blocks.state.state_values import prop_as_bool
from ..blocks.models.api import collision_aabbs_for_block

from .block_pick import BlockPick, pick_block
from .placement_policy import PlacementPolicy

INTERACTION_ACTION_BREAK = "break"
INTERACTION_ACTION_PLACE = "place"
INTERACTION_ACTION_INTERACT = "interact"


@dataclass(frozen=True)
class InteractionOutcome:
    success: bool
    action: str | None = None
    target_block_state: str | None = None
    target_position: tuple[int, int, int] | None = None


@dataclass
class InteractionService:
    world: WorldState
    player: PlayerEntity
    block_registry: BlockRegistry
    placement_policy: PlacementPolicy = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.placement_policy = PlacementPolicy(block_registry=self.block_registry)

    @classmethod
    def create(cls, *, world: WorldState, player: PlayerEntity, block_registry: BlockRegistry) -> "InteractionService":
        return cls(world=world, player=player, block_registry=block_registry)

    def pick_block(self, reach: float=5.0, *, origin: Vec3 | None=None, direction: Vec3 | None=None) -> BlockPick | None:
        return self._pick_target(reach=float(reach), origin=origin, direction=direction)

    def _pick_target(self, reach: float, *, origin: Vec3 | None=None, direction: Vec3 | None=None) -> BlockPick | None:
        eye = self.player.eye_pos() if origin is None else origin
        direction = self.player.view_forward() if direction is None else direction
        return pick_block(self.world, origin=eye, direction=direction, reach=float(reach), block_registry=self.block_registry)

    def _commit_world_edit(self, *, updates: dict[tuple[int, int, int], str] | None=None, removals: tuple[tuple[int, int, int], ...]=()) -> None:
        normalized_updates = {(int(k[0]), int(k[1]), int(k[2])): str(v) for k, v in (updates or {}).items()}
        normalized_removals = tuple((int(k[0]), int(k[1]), int(k[2])) for k in removals)
        touched = set(normalized_updates.keys()) | set(normalized_removals)
        if not touched:
            return

        structural_updates = collect_structural_neighbor_updates(self.world, touched, block_registry=self.block_registry, overlay_updates=normalized_updates, overlay_removals=normalized_removals)
        final_updates = dict(normalized_updates)
        final_updates.update(structural_updates)
        self.world.set_blocks_bulk(updates=final_updates, removals=normalized_removals)

    def break_block(self, reach: float=5.0, *, origin: Vec3 | None=None, direction: Vec3 | None=None) -> InteractionOutcome:
        hit = self._pick_target(reach=float(reach), origin=origin, direction=direction)
        if hit is None:
            return InteractionOutcome(success=False)

        hx, hy, hz = hit.hit
        previous_state = self.world.blocks.get((int(hx), int(hy), int(hz)))
        if previous_state is None:
            return InteractionOutcome(success=False)

        self._commit_world_edit(removals=((int(hx), int(hy), int(hz)),))
        return InteractionOutcome(success=True, action=INTERACTION_ACTION_BREAK, target_block_state=str(previous_state), target_position=(int(hx), int(hy), int(hz)))

    def _player_intersects_state(self, *, cell: tuple[int, int, int], state_str: str) -> bool:
        px, py, pz = (int(cell[0]), int(cell[1]), int(cell[2]))
        player_aabb = self.player.aabb_at(self.player.position)

        def get_state(x: int, y: int, z: int) -> str | None:
            key = (int(x), int(y), int(z))
            if key == (int(px), int(py), int(pz)):
                return str(state_str)
            return self.world.blocks.get(key)

        for box in collision_aabbs_for_block(str(state_str), get_state, self.block_registry.get, int(px), int(py), int(pz)):
            if player_aabb.intersects(box):
                return True
        return False

    def _toggle_fence_gate_if_hit(self, hit_cell: tuple[int, int, int]) -> InteractionOutcome:
        k = (int(hit_cell[0]), int(hit_cell[1]), int(hit_cell[2]))
        st = self.world.blocks.get(k)
        if st is None:
            return InteractionOutcome(success=False)

        base, props = parse_state(st)
        d = self.block_registry.get(str(base))
        if d is None or (not is_fence_gate(d)):
            return InteractionOutcome(success=False)

        is_open = prop_as_bool(props, "open", False)
        facing = normalize_cardinal(str(props.get("facing", "south")), default="south")
        powered = prop_as_bool(props, "powered", False)
        waterlogged = prop_as_bool(props, "waterlogged", False)
        in_wall = prop_as_bool(props, "in_wall", False)

        next_open = not bool(is_open)
        next_facing = str(facing)

        if bool(next_open):
            px = float(self.player.position.x)
            pz = float(self.player.position.z)
            cx = float(k[0]) + 0.5
            cz = float(k[2]) + 0.5
            dx = px - cx
            dz = pz - cz

            fx, fz = facing_vec_xz(str(facing))
            dot = float(dx) * float(fx) + float(dz) * float(fz)

            if dot > 1e-9:
                next_facing = opposite_cardinal(str(facing))

        nxt = canonical_fence_gate_state(self.world, int(k[0]), int(k[1]), int(k[2]), block_registry=self.block_registry, facing_override=str(next_facing), open_override=bool(next_open))

        if nxt is None:
            nxt = make_fence_gate_state(str(base), str(next_facing), open_state=bool(next_open), powered=bool(powered), in_wall=bool(in_wall), waterlogged=bool(waterlogged))

        self._commit_world_edit(updates={k: str(nxt)})

        if bool(next_open):
            if self.player.fence_gate_overlap_exemption == k:
                self.player.fence_gate_overlap_exemption = None
        elif self._player_intersects_state(cell=k, state_str=str(nxt)):
            self.player.fence_gate_overlap_exemption = k
        elif self.player.fence_gate_overlap_exemption == k:
            self.player.fence_gate_overlap_exemption = None

        return InteractionOutcome(success=True, action=INTERACTION_ACTION_INTERACT, target_block_state=str(nxt), target_position=(int(k[0]), int(k[1]), int(k[2])))

    def interact_block_at_hit(self, hit_cell: tuple[int, int, int]) -> InteractionOutcome:
        return self._toggle_fence_gate_if_hit(hit_cell)

    def _apply_place_state(self, *, cell: tuple[int, int, int], place_state: str) -> InteractionOutcome:
        px, py, pz = (int(cell[0]), int(cell[1]), int(cell[2]))

        if self.placement_policy.placement_intersects_player(player=self.player, world=self.world, px=int(px), py=int(py), pz=int(pz), place_state=str(place_state)):
            return InteractionOutcome(success=False)

        self._commit_world_edit(updates={(int(px), int(py), int(pz)): str(place_state)})
        return InteractionOutcome(success=True, action=INTERACTION_ACTION_PLACE, target_block_state=str(place_state), target_position=(int(px), int(py), int(pz)))

    def _has_selected_placeable_block(self, block_id: str) -> bool:
        bid = str(block_id).strip()
        if not bid:
            return False
        return self.block_registry.get(str(bid)) is not None

    def _place_from_hit(self, *, hit: BlockPick, block_id: str | None) -> InteractionOutcome:
        bid = "" if block_id is None else str(block_id).strip()
        if not self._has_selected_placeable_block(str(bid)):
            return InteractionOutcome(success=False)

        hx, hy, hz = hit.hit
        hit_cell = (int(hx), int(hy), int(hz))
        hit_state = self.world.blocks.get(hit_cell)

        if hit_state is not None:
            merge_hit_state = self.placement_policy.resolve_slab_merge_state_from_hit(existing_state=str(hit_state), block_id=str(bid), hit_face=int(hit.face))
            if merge_hit_state is not None:
                return self._apply_place_state(cell=hit_cell, place_state=str(merge_hit_state))

        if hit_state is None:
            return InteractionOutcome(success=False)

        if hit.place is None:
            return InteractionOutcome(success=False)

        px, py, pz = hit.place
        place_cell = (int(px), int(py), int(pz))
        existing_place_state = self.world.blocks.get(place_cell)

        if existing_place_state is not None:
            merge_place_state = self.placement_policy.resolve_slab_merge_state(existing_state=str(existing_place_state), block_id=str(bid), hit_face=int(hit.face), hit_point=hit.hit_point)
            if merge_place_state is None:
                return InteractionOutcome(success=False)

            return self._apply_place_state(cell=place_cell, place_state=str(merge_place_state))

        place_state = self.placement_policy.resolve_place_state(player=self.player, block_id=str(bid), hit_face=int(hit.face), hit_point=hit.hit_point)
        if place_state is None:
            return InteractionOutcome(success=False)

        return self._apply_place_state(cell=place_cell, place_state=str(place_state))

    def place_block_from_hit(self, hit: BlockPick, block_id: str | None) -> InteractionOutcome:
        return self._place_from_hit(hit=hit, block_id=block_id)

    def place_block(self, block_id: str | None, reach: float=5.0, *, crouching: bool=False, origin: Vec3 | None=None, direction: Vec3 | None=None) -> InteractionOutcome:
        hit = self.pick_block(reach=float(reach), origin=origin, direction=direction)
        if hit is None:
            return InteractionOutcome(success=False)

        if bool(crouching):
            return self.place_block_from_hit(hit, block_id)

        interact_outcome = self.interact_block_at_hit(hit.hit)
        if bool(interact_outcome.success):
            return interact_outcome

        return self.place_block_from_hit(hit, block_id)
