# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/facade/player_render_state.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FirstPersonRenderState:
    visible_block_id: str | None
    visible_block_kind: str | None
    target_block_id: str | None
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


@dataclass(frozen=True)
class PlayerRenderState:
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
