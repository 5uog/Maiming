# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/passes/held_block_pass.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from ....core.math.vec3 import Vec3
from ....domain.blocks.block_definition import BlockDefinition
from ..resources.texture_atlas import TextureAtlas
from ....application.rendering.first_person_geometry import build_first_person_held_block_face_rows
from ....application.rendering.player_render_state import FirstPersonRenderState
from .textured_face_pass import TexturedFacePass
from ..gl.shader_program import ShaderProgram

UVRect = tuple[float, float, float, float]


@dataclass
class HeldBlockPass:
    _face_pass: TexturedFacePass | None = None
    _atlas: TextureAtlas | None = None
    _uv_lookup: Callable[[str, int], UVRect] | None = None
    _def_lookup: Callable[[str], BlockDefinition | None] | None = None

    def initialize(self, *, prog: ShaderProgram, atlas: TextureAtlas, uv_lookup, def_lookup) -> None:
        self._face_pass = TexturedFacePass()
        self._face_pass.initialize(prog)
        self._atlas = atlas
        self._uv_lookup = uv_lookup
        self._def_lookup = def_lookup

    def destroy(self) -> None:
        if self._face_pass is not None:
            self._face_pass.destroy()
        self._face_pass = None
        self._atlas = None
        self._uv_lookup = None
        self._def_lookup = None

    def draw(self, *, first_person: FirstPersonRenderState | None, view_proj: np.ndarray, sun_dir: Vec3) -> tuple[int, int]:
        if self._face_pass is None or self._atlas is None or self._uv_lookup is None or self._def_lookup is None:
            return (0, 0)

        rows = build_first_person_held_block_face_rows(first_person, projection=view_proj, uv_lookup=self._uv_lookup, def_lookup=self._def_lookup)
        return self._face_pass.draw(face_rows=rows, view_proj=view_proj, tex_id=int(self._atlas.tex_id), sun_dir=sun_dir)
