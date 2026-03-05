# FILE: src/maiming/infrastructure/rendering/opengl/facade/gl_resources.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from OpenGL.GL import glGenVertexArrays, glDeleteVertexArrays

from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.default_registry import create_default_registry

from .._internal.gl.shader_program import ShaderProgram
from .._internal.gl.mesh_buffer import MeshBuffer
from .._internal.resources.texture_atlas import TextureAtlas

@dataclass
class GLResources:
    world_prog: ShaderProgram
    shadow_prog: ShaderProgram
    sun_prog: ShaderProgram
    cloud_prog: ShaderProgram
    selection_prog: ShaderProgram

    cloud_mesh: MeshBuffer

    atlas: TextureAtlas
    empty_vao: int

    blocks: BlockRegistry

    @staticmethod
    def load(assets_dir: Path) -> "GLResources":
        shader_dir = Path(__file__).resolve().parents[1] / "_internal" / "shaders"

        world_prog = ShaderProgram.from_files(shader_dir / "world.vert", shader_dir / "world.frag")
        shadow_prog = ShaderProgram.from_files(shader_dir / "shadow.vert", shader_dir / "shadow.frag")
        sun_prog = ShaderProgram.from_files(shader_dir / "sun.vert", shader_dir / "sun.frag")
        cloud_prog = ShaderProgram.from_files(shader_dir / "cloud_box.vert", shader_dir / "cloud_box.frag")
        selection_prog = ShaderProgram.from_files(
            shader_dir / "selection_line.vert",
            shader_dir / "selection_line.frag",
        )

        cloud_mesh = MeshBuffer.create_cube_instanced()

        blocks = create_default_registry()
        tex_names = blocks.required_texture_names()

        atlas = TextureAtlas.build_from_dir(
            assets_dir / "minecraft" / "textures" / "block",
            tile_size=64,
            names=tex_names,
            pad=1,
        )

        empty_vao = int(glGenVertexArrays(1))

        return GLResources(
            world_prog=world_prog,
            shadow_prog=shadow_prog,
            sun_prog=sun_prog,
            cloud_prog=cloud_prog,
            selection_prog=selection_prog,
            cloud_mesh=cloud_mesh,
            atlas=atlas,
            empty_vao=empty_vao,
            blocks=blocks,
        )

    def destroy(self) -> None:
        self.cloud_mesh.destroy()
        self.atlas.destroy()

        self.world_prog.destroy()
        self.shadow_prog.destroy()
        self.sun_prog.destroy()
        self.cloud_prog.destroy()
        self.selection_prog.destroy()

        if int(self.empty_vao) != 0:
            glDeleteVertexArrays(1, [int(self.empty_vao)])
            self.empty_vao = 0