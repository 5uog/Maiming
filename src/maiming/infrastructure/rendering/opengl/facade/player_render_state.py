# FILE: src/maiming/infrastructure/rendering/opengl/facade/player_render_state.py
from __future__ import annotations
from dataclasses import dataclass

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