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
class RenderSnapshotDTO:
    world_revision: int
    camera: CameraDTO