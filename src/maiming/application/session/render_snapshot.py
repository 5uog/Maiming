# FILE: src/maiming/application/session/render_snapshot.py
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

    is_first_person: bool = True

@dataclass(frozen=True)
class RenderSnapshotDTO:
    world_revision: int
    camera: CameraDTO
    player_model: PlayerModelSnapshotDTO