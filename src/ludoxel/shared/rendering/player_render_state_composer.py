# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from .render_snapshot import PlayerModelSnapshotDTO, RenderSnapshotDTO
from ...features.othello.domain.inventory.special_items import get_special_item_descriptor
from ..blocks.registry.block_registry import BlockRegistry
from .first_person_motion import FirstPersonMotionSample
from .player_render_state import FirstPersonRenderState, PlayerRenderState


def compose_player_render_state(*, snapshot: RenderSnapshotDTO, motion: FirstPersonMotionSample, block_registry: BlockRegistry) -> PlayerRenderState:
    """I define R(snapshot, motion) = Compose(snapshot.player_model, motion, registry). I keep this outer adapter so that the main render snapshot can be projected onto the player-render state without duplicating DTO field selection at every call site."""
    return compose_player_render_state_from_parts(player_model=snapshot.player_model, motion=motion, block_registry=block_registry)


def compose_player_render_state_from_parts(*, player_model: PlayerModelSnapshotDTO, motion: FirstPersonMotionSample, block_registry: BlockRegistry) -> PlayerRenderState:
    """I define the composed player render state as the direct product of the authoritative player-model snapshot and the sampled first-person motion state, enriched by registry and special-item lookups. I use this pure constructor to turn runtime DTOs into the immutable render-state records consumed by the pose builders."""
    visible_def = None if motion.visible_item_id is None else block_registry.get(str(motion.visible_item_id))
    special_descriptor = None if motion.visible_item_id is None else get_special_item_descriptor(motion.visible_item_id)
    first_person = FirstPersonRenderState(visible_item_id=motion.visible_item_id, target_item_id=motion.target_item_id, visible_block_id=None if visible_def is None else str(motion.visible_item_id), visible_block_kind=None if visible_def is None else str(visible_def.kind), visible_special_item_icon=None if special_descriptor is None else str(special_descriptor.icon_key), equip_progress=float(motion.equip_progress), prev_equip_progress=float(motion.prev_equip_progress), swing_progress=float(motion.swing_progress), prev_swing_progress=float(motion.prev_swing_progress), show_arm=bool(motion.show_arm), show_view_model=bool(motion.show_view_model), slim_arm=bool(motion.slim_arm), view_bob_x=float(player_model.first_person_tx), view_bob_y=float(player_model.first_person_ty), view_bob_z=float(player_model.first_person_tz), view_bob_yaw_deg=float(player_model.first_person_yaw_deg), view_bob_pitch_deg=float(player_model.first_person_pitch_deg), view_bob_roll_deg=float(player_model.first_person_roll_deg))
    return PlayerRenderState(base_x=float(player_model.base_x), base_y=float(player_model.base_y), base_z=float(player_model.base_z), body_yaw_deg=float(player_model.body_yaw_deg), head_yaw_deg=float(player_model.head_yaw_deg), head_pitch_deg=float(player_model.head_pitch_deg), limb_phase_rad=float(player_model.limb_phase_rad), limb_swing_amount=float(player_model.limb_swing_amount), crouch_amount=float(player_model.crouch_amount), is_first_person=bool(player_model.is_first_person), first_person=first_person)
