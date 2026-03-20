# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from ....application.context.runtime.render_snapshot import PlayerModelSnapshotDTO, RenderSnapshotDTO
from ....shared.domain.blocks.registry.block_registry import BlockRegistry
from ....shared.application.rendering.player_render_state import FirstPersonRenderState, PlayerRenderState
from .first_person_motion import FirstPersonMotionSample

def compose_player_render_state(*, snapshot: RenderSnapshotDTO, motion: FirstPersonMotionSample, block_registry: BlockRegistry) -> PlayerRenderState:
    return compose_player_render_state_from_parts(player_model=snapshot.player_model, motion=motion, block_registry=block_registry)

def compose_player_render_state_from_parts(*, player_model: PlayerModelSnapshotDTO, motion: FirstPersonMotionSample, block_registry: BlockRegistry) -> PlayerRenderState:
    visible_def = None if motion.visible_block_id is None else block_registry.get(str(motion.visible_block_id))
    first_person = FirstPersonRenderState(visible_block_id=motion.visible_block_id, visible_block_kind=None if visible_def is None else str(visible_def.kind), target_block_id=motion.target_block_id, equip_progress=float(motion.equip_progress), prev_equip_progress=float(motion.prev_equip_progress), swing_progress=float(motion.swing_progress), prev_swing_progress=float(motion.prev_swing_progress), show_arm=bool(motion.show_arm), show_view_model=bool(motion.show_view_model), slim_arm=bool(motion.slim_arm), view_bob_x=float(player_model.first_person_tx), view_bob_y=float(player_model.first_person_ty), view_bob_z=float(player_model.first_person_tz), view_bob_yaw_deg=float(player_model.first_person_yaw_deg), view_bob_pitch_deg=float(player_model.first_person_pitch_deg), view_bob_roll_deg=float(player_model.first_person_roll_deg))
    return PlayerRenderState(base_x=float(player_model.base_x), base_y=float(player_model.base_y), base_z=float(player_model.base_z), body_yaw_deg=float(player_model.body_yaw_deg), head_yaw_deg=float(player_model.head_yaw_deg), head_pitch_deg=float(player_model.head_pitch_deg), limb_phase_rad=float(player_model.limb_phase_rad), limb_swing_amount=float(player_model.limb_swing_amount), crouch_amount=float(player_model.crouch_amount), is_first_person=bool(player_model.is_first_person), first_person=first_person)