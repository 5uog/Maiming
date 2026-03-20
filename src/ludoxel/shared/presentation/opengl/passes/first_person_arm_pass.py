# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/passes/first_person_arm_pass.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ludoxel.shared.core.math.vec3 import Vec3
from ludoxel.shared.presentation.opengl.resources.image_texture import ImageTexture
from ludoxel.shared.application.rendering.first_person_geometry import build_first_person_arm_face_rows
from ludoxel.shared.application.rendering.player_render_state import FirstPersonRenderState
from ludoxel.shared.presentation.opengl.passes.textured_face_pass import TexturedFacePass
from ludoxel.shared.presentation.opengl.gl.shader_program import ShaderProgram


@dataclass
class FirstPersonArmPass:
    _face_pass: TexturedFacePass | None = None
    _skin_texture: ImageTexture | None = None

    def initialize(self, *, prog: ShaderProgram, skin_texture: ImageTexture) -> None:
        self._face_pass = TexturedFacePass()
        self._face_pass.initialize(prog)
        self._skin_texture = skin_texture

    def destroy(self) -> None:
        if self._face_pass is not None:
            self._face_pass.destroy()
        self._face_pass = None
        self._skin_texture = None

    def draw(self, *, first_person: FirstPersonRenderState | None, view_proj: np.ndarray, sun_dir: Vec3) -> tuple[int, int]:
        if self._face_pass is None or self._skin_texture is None:
            return (0, 0)

        rows = build_first_person_arm_face_rows(first_person, projection=view_proj, skin_width=int(self._skin_texture.width), skin_height=int(self._skin_texture.height))
        return self._face_pass.draw(face_rows=rows, view_proj=view_proj, tex_id=int(self._skin_texture.tex_id), sun_dir=sun_dir)
