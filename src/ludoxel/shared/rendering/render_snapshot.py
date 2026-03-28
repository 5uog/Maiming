# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraDTO:
    eye_x: float
    eye_y: float
    eye_z: float
    yaw_deg: float
    pitch_deg: float
    fov_deg: float
    shake_tx: float = 0.0
    shake_ty: float = 0.0
    shake_tz: float = 0.0
    shake_yaw_deg: float = 0.0
    shake_pitch_deg: float = 0.0
    shake_roll_deg: float = 0.0


@dataclass(frozen=True)
class PlayerModelSnapshotDTO:
    base_x: float
    base_y: float
    base_z: float
    body_yaw_deg: float
    head_yaw_deg: float
    head_pitch_deg: float
    limb_phase_rad: float
    limb_swing_amount: float
    crouch_amount: float
    first_person_tx: float = 0.0
    first_person_ty: float = 0.0
    first_person_tz: float = 0.0
    first_person_yaw_deg: float = 0.0
    first_person_pitch_deg: float = 0.0
    first_person_roll_deg: float = 0.0
    is_first_person: bool = True


@dataclass(frozen=True)
class FallingBlockRenderSampleDTO:
    state_str: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class RenderSnapshotDTO:
    world_revision: int
    camera: CameraDTO
    player_model: PlayerModelSnapshotDTO
    falling_blocks: tuple[FallingBlockRenderSampleDTO, ...] = ()
