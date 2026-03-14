# FILE: src/maiming/application/services/interaction_service.py
from __future__ import annotations
from dataclasses import dataclass, field

from ...core.math.vec3 import Vec3
from ...domain.world.world_state import WorldState
from ...domain.entities.player_entity import PlayerEntity

from ...domain.blocks.block_registry import BlockRegistry
from ...domain.blocks.state_codec import parse_state
from ...domain.blocks.cardinal import normalize_cardinal, opposite_cardinal, facing_vec_xz
from ...domain.blocks.connectivity import make_fence_gate_state, canonical_fence_gate_state, refresh_structural_neighbors
from ...domain.blocks.structural_rules import is_fence_gate
from ...domain.blocks.state_values import prop_as_bool

from ...domain.systems.build_system import BlockPick, pick_block

from .placement_policy import PlacementPolicy

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

    def _pick_target(self, reach: float, *, origin: Vec3 | None = None, direction: Vec3 | None = None) -> BlockPick | None:
        eye = self.player.eye_pos() if origin is None else origin
        direction = self.player.view_forward() if direction is None else direction
        return pick_block(self.world, origin=eye, direction=direction, reach=float(reach), block_registry=self.block_registry)

    def break_block(self, reach: float = 5.0, *, origin: Vec3 | None = None, direction: Vec3 | None = None) -> bool:
        hit = self._pick_target(reach=float(reach), origin=origin, direction=direction)
        if hit is None:
            return False

        hx, hy, hz = hit.hit
        self.world.remove_block(int(hx), int(hy), int(hz))
        refresh_structural_neighbors(self.world, int(hx), int(hy), int(hz), block_registry=self.block_registry)
        return True

    def _toggle_fence_gate_if_hit(self, hit_cell: tuple[int, int, int]) -> bool:
        k = (int(hit_cell[0]), int(hit_cell[1]), int(hit_cell[2]))
        st = self.world.blocks.get(k)
        if st is None:
            return False

        base, props = parse_state(st)
        d = self.block_registry.get(str(base))
        if d is None or (not is_fence_gate(d)):
            return False

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

        self.world.set_block(int(k[0]), int(k[1]), int(k[2]), str(nxt))
        refresh_structural_neighbors(self.world, int(k[0]), int(k[1]), int(k[2]), block_registry=self.block_registry)
        return True

    def _apply_place_state(self, *, cell: tuple[int, int, int], place_state: str) -> bool:
        px, py, pz = (int(cell[0]), int(cell[1]), int(cell[2]))

        if self.placement_policy.placement_intersects_player(player=self.player, world=self.world, px=int(px), py=int(py), pz=int(pz), place_state=str(place_state)):
            return False

        self.world.set_block(int(px), int(py), int(pz), str(place_state))
        refresh_structural_neighbors(self.world, int(px), int(py), int(pz), block_registry=self.block_registry)
        return True

    def _has_selected_placeable_block(self, block_id: str) -> bool:
        bid = str(block_id).strip()
        if not bid:
            return False
        return self.block_registry.get(str(bid)) is not None

    def _place_from_hit(self, *, hit: BlockPick, block_id: str | None) -> bool:
        bid = "" if block_id is None else str(block_id).strip()
        if not self._has_selected_placeable_block(str(bid)):
            return False

        hx, hy, hz = hit.hit
        hit_cell = (int(hx), int(hy), int(hz))
        hit_state = self.world.blocks.get(hit_cell)

        if hit_state is not None:
            merge_hit_state = self.placement_policy.resolve_slab_merge_state_from_hit(existing_state=str(hit_state), block_id=str(bid), hit_face=int(hit.face))
            if merge_hit_state is not None:
                return self._apply_place_state(cell=hit_cell, place_state=str(merge_hit_state))

        if hit.place is None:
            return False

        px, py, pz = hit.place
        place_cell = (int(px), int(py), int(pz))
        existing_place_state = self.world.blocks.get(place_cell)

        if existing_place_state is not None:
            merge_place_state = self.placement_policy.resolve_slab_merge_state(existing_state=str(existing_place_state), block_id=str(bid), hit_face=int(hit.face), hit_point=hit.hit_point)
            if merge_place_state is None:
                return False

            return self._apply_place_state(cell=place_cell, place_state=str(merge_place_state))

        place_state = self.placement_policy.resolve_place_state(player=self.player, block_id=str(bid), hit_face=int(hit.face), hit_point=hit.hit_point)
        if place_state is None:
            return False

        return self._apply_place_state(cell=place_cell, place_state=str(place_state))

    def place_block(self, block_id: str | None, reach: float = 5.0, *, crouching: bool = False, origin: Vec3 | None = None, direction: Vec3 | None = None) -> bool:
        hit = self._pick_target(reach=float(reach), origin=origin, direction=direction)
        if hit is None:
            return False

        if bool(crouching):
            return self._place_from_hit(hit=hit, block_id=block_id)

        if self._toggle_fence_gate_if_hit(hit.hit):
            return True

        return self._place_from_hit(hit=hit, block_id=block_id)