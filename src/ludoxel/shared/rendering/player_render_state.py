# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FirstPersonRenderState:
    """I define this record as the immutable parameter vector consumed by first-person arm, held-block, and special-item renderers. I keep both visible and target identifiers together with temporal animation channels so that one sampled state suffices to reconstruct every view-model transform of the frame."""
    visible_item_id: str | None
    target_item_id: str | None
    visible_block_id: str | None
    visible_block_kind: str | None
    visible_special_item_icon: str | None
    equip_progress: float
    prev_equip_progress: float
    swing_progress: float
    prev_swing_progress: float
    show_arm: bool
    show_view_model: bool
    slim_arm: bool
    view_bob_x: float = 0.0
    view_bob_y: float = 0.0
    view_bob_z: float = 0.0
    view_bob_yaw_deg: float = 0.0
    view_bob_pitch_deg: float = 0.0
    view_bob_roll_deg: float = 0.0
    arm_rotation_limit_min_deg: float = -180.0
    arm_rotation_limit_max_deg: float = 180.0


@dataclass(frozen=True)
class PlayerRenderState:
    """I define this record as the immutable player-pose input P = (base pose, locomotion phase, crouch, perspective flag, first-person extension). I use it as the cache key for player model synthesis because every visible body and shadow pose derives from exactly these fields."""
    base_x: float
    base_y: float
    base_z: float
    body_yaw_deg: float
    head_yaw_deg: float
    head_pitch_deg: float
    limb_phase_rad: float
    limb_swing_amount: float
    crouch_amount: float
    is_first_person: bool = True
    first_person: FirstPersonRenderState | None = None
