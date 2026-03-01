# FILE: src/maiming/application/ports/renderer_port.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class BlockInstanceDTO:
    x: int
    y: int
    z: int
    block_id: str

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
    blocks: list[BlockInstanceDTO]
    camera: CameraDTO

class RendererPort(Protocol):
    def submit_snapshot(self, snapshot: RenderSnapshotDTO) -> None:
        ...