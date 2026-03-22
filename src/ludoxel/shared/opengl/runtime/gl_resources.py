# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from OpenGL.GL import glGenVertexArrays, glDeleteVertexArrays
from PyQt6.QtGui import QImage

from ...blocks.registry.block_registry import BlockRegistry
from ..gl.shader_program import ShaderProgram
from ..gl.mesh_buffer import MeshBuffer
from ..resources.image_texture import ImageTexture
from ..resources.texture_atlas import TextureAtlas


@dataclass
class GLResources:
    world_prog: ShaderProgram
    world_no_shadow_prog: ShaderProgram
    shadow_prog: ShaderProgram
    sun_prog: ShaderProgram
    cloud_prog: ShaderProgram
    selection_prog: ShaderProgram
    othello_prog: ShaderProgram
    othello_shadow_prog: ShaderProgram
    chunk_face_payload_prog: ShaderProgram
    first_person_face_prog: ShaderProgram

    player_model_shadow_prog: ShaderProgram

    cloud_mesh: MeshBuffer

    atlas: TextureAtlas
    skin_texture: ImageTexture
    empty_vao: int

    blocks: BlockRegistry

    @staticmethod
    def load(assets_dir: Path, *, blocks: BlockRegistry) -> "GLResources":
        shader_dir = Path(__file__).resolve().parents[1] / "shaders"
        othello_shader_dir = Path(__file__).resolve().parents[3] / "features" / "othello" / "opengl" / "shaders"

        world_prog = ShaderProgram.from_files(shader_dir / "world.vert", shader_dir / "world.frag")
        world_no_shadow_prog = ShaderProgram.from_files(shader_dir / "world.vert", shader_dir / "world_no_shadow.frag")
        shadow_prog = ShaderProgram.from_files(shader_dir / "shadow.vert", shader_dir / "shadow.frag")
        sun_prog = ShaderProgram.from_files(shader_dir / "sun.vert", shader_dir / "sun.frag")
        cloud_prog = ShaderProgram.from_files(shader_dir / "cloud_box.vert", shader_dir / "cloud_box.frag")
        selection_prog = ShaderProgram.from_files(shader_dir / "selection_line.vert", shader_dir / "selection_line.frag")
        othello_prog = ShaderProgram.from_files(othello_shader_dir / "othello.vert", othello_shader_dir / "othello.frag")
        othello_shadow_prog = ShaderProgram.from_files(othello_shader_dir / "othello_shadow.vert", shader_dir / "shadow.frag")
        chunk_face_payload_prog = ShaderProgram.from_compute_file(shader_dir / "chunk_face_payload.comp")
        first_person_face_prog = ShaderProgram.from_files(shader_dir / "first_person_face.vert", shader_dir / "first_person_face.frag")
        player_model_shadow_prog = ShaderProgram.from_files(shader_dir / "player_model_shadow.vert", shader_dir / "shadow.frag")

        cloud_mesh = MeshBuffer.create_cube_instanced()

        tex_names = blocks.required_texture_names()

        atlas = TextureAtlas.build_from_dir(assets_dir / "minecraft" / "textures" / "block", tile_size=64, names=tex_names, pad=1)
        skin_texture = ImageTexture.load(assets_dir / "minecraft" / "skins" / "alex.png")

        empty_vao = int(glGenVertexArrays(1))

        return GLResources(world_prog=world_prog, world_no_shadow_prog=world_no_shadow_prog, shadow_prog=shadow_prog, sun_prog=sun_prog, cloud_prog=cloud_prog, selection_prog=selection_prog, othello_prog=othello_prog, othello_shadow_prog=othello_shadow_prog, chunk_face_payload_prog=chunk_face_payload_prog, first_person_face_prog=first_person_face_prog, player_model_shadow_prog=player_model_shadow_prog, cloud_mesh=cloud_mesh, atlas=atlas, skin_texture=skin_texture, empty_vao=empty_vao, blocks=blocks)

    def destroy(self) -> None:
        self.cloud_mesh.destroy()
        self.atlas.destroy()
        self.skin_texture.destroy()

        self.world_prog.destroy()
        self.world_no_shadow_prog.destroy()
        self.shadow_prog.destroy()
        self.sun_prog.destroy()
        self.cloud_prog.destroy()
        self.selection_prog.destroy()
        self.othello_prog.destroy()
        self.othello_shadow_prog.destroy()
        self.chunk_face_payload_prog.destroy()
        self.first_person_face_prog.destroy()
        self.player_model_shadow_prog.destroy()

        if int(self.empty_vao) != 0:
            glDeleteVertexArrays(1,[int(self.empty_vao)])
            self.empty_vao = 0

    def replace_skin_texture(self, image: QImage) -> ImageTexture:
        next_texture = ImageTexture.from_image(image)
        previous_texture = self.skin_texture
        self.skin_texture = next_texture
        previous_texture.destroy()
        return self.skin_texture
