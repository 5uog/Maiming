# FILE: src/maiming/presentation/widgets/viewport/viewport_world_upload.py
from __future__ import annotations

from dataclasses import dataclass

from maiming.application.ports.renderer_port import RenderSnapshotDTO
from maiming.infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer

@dataclass
class WorldUploadTracker:
    """
    The renderer consumes a block list keyed by a monotonically increasing world revision.
    This tracker preserves the existing upload policy by submitting world geometry only when
    the revision changes, which keeps CPU-to-GPU traffic bounded under steady camera motion.
    """
    last_uploaded_revision: int = -1

    def upload_if_needed(self, *, snap: RenderSnapshotDTO, renderer: GLRenderer) -> None:
        if int(snap.world_revision) == int(self.last_uploaded_revision):
            return

        blocks = [(b.x, b.y, b.z, b.block_id) for b in snap.blocks]
        renderer.submit_world(world_revision=int(snap.world_revision), blocks=blocks)
        self.last_uploaded_revision = int(snap.world_revision)