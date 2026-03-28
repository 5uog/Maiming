# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ...math.vec3 import Vec3
from ...rendering.first_person_geometry import build_first_person_special_item_face_rows
from ...rendering.player_render_state import FirstPersonRenderState
from ....features.othello.ui.special_item_art import build_special_item_icon_image
from ..gl.shader_program import ShaderProgram
from ..resources.image_texture import ImageTexture
from .textured_face_pass import TexturedFacePass


@dataclass
class SpecialItemPass:
    _face_pass: TexturedFacePass | None = None
    _textures: dict[str, ImageTexture] = field(default_factory=dict)

    def initialize(self, *, prog: ShaderProgram) -> None:
        self._face_pass = TexturedFacePass()
        self._face_pass.initialize(prog)
        self._textures = {"start": ImageTexture.from_image(build_special_item_icon_image("start", size=192)), "settings": ImageTexture.from_image(build_special_item_icon_image("settings", size=192))}

    def destroy(self) -> None:
        if self._face_pass is not None:
            self._face_pass.destroy()
        self._face_pass = None
        for texture in self._textures.values():
            texture.destroy()
        self._textures.clear()

    def draw(self, *, first_person: FirstPersonRenderState | None, view_proj: np.ndarray, sun_dir: Vec3) -> tuple[int, int]:
        if self._face_pass is None or first_person is None:
            return (0, 0)

        icon_key = None if first_person.visible_special_item_icon is None else str(first_person.visible_special_item_icon)
        texture = None if icon_key is None else self._textures.get(icon_key)
        if texture is None:
            return (0, 0)

        rows = build_first_person_special_item_face_rows(first_person, projection=view_proj)
        return self._face_pass.draw(face_rows=rows, view_proj=view_proj, tex_id=int(texture.tex_id), sun_dir=sun_dir)
