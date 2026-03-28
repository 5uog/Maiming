# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...math.vec3 import Vec3
from ...rendering.faces.block_break_particle_face_rows import build_block_break_particle_face_rows
from ...rendering.render_snapshot import BlockBreakParticleRenderSampleDTO
from ..gl.shader_program import ShaderProgram
from ..resources.texture_atlas import TextureAtlas
from .textured_face_pass import TexturedFacePass


@dataclass
class BlockBreakParticlePass:
    _face_pass: TexturedFacePass | None = None
    _atlas: TextureAtlas | None = None

    def initialize(self, *, prog: ShaderProgram, atlas: TextureAtlas) -> None:
        self._face_pass = TexturedFacePass()
        self._face_pass.initialize(prog)
        self._atlas = atlas

    def destroy(self) -> None:
        if self._face_pass is not None:
            self._face_pass.destroy()
        self._face_pass = None
        self._atlas = None

    def draw(self, *, samples: tuple[BlockBreakParticleRenderSampleDTO, ...], view_proj: np.ndarray, sun_dir: Vec3, camera_forward: Vec3) -> tuple[int, int]:
        if self._face_pass is None or self._atlas is None:
            return (0, 0)

        rows = build_block_break_particle_face_rows(samples=samples, camera_forward=camera_forward)
        return self._face_pass.draw(face_rows=rows, view_proj=view_proj, tex_id=int(self._atlas.tex_id), sun_dir=sun_dir)
