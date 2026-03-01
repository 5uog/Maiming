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

    world_meshes: list[MeshBuffer]
    cloud_mesh: MeshBuffer
    shadow_cube_mesh: MeshBuffer

    atlas: TextureAtlas
    empty_vao: int

    blocks: BlockRegistry

    @staticmethod
    def load(assets_dir: Path) -> "GLResources":
        # Shaders are internal implementation assets; the facade resolves them from the _internal tree.
        shader_dir = Path(__file__).resolve().parents[1] / "_internal" / "shaders"

        world_prog = ShaderProgram.from_files(shader_dir / "world.vert", shader_dir / "world.frag")
        shadow_prog = ShaderProgram.from_files(shader_dir / "shadow.vert", shader_dir / "shadow.frag")
        sun_prog = ShaderProgram.from_files(shader_dir / "sun.vert", shader_dir / "sun.frag")
        cloud_prog = ShaderProgram.from_files(shader_dir / "cloudBox.vert", shader_dir / "cloudBox.frag")

        world_meshes = [MeshBuffer.create_quad_instanced(i) for i in range(6)]
        cloud_mesh = MeshBuffer.create_cube_instanced()
        shadow_cube_mesh = MeshBuffer.create_cube_instanced()

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
            world_meshes=world_meshes,
            cloud_mesh=cloud_mesh,
            shadow_cube_mesh=shadow_cube_mesh,
            atlas=atlas,
            empty_vao=empty_vao,
            blocks=blocks,
        )

    def destroy(self) -> None:
        for m in self.world_meshes:
            m.destroy()
        self.cloud_mesh.destroy()
        self.shadow_cube_mesh.destroy()

        self.atlas.destroy()

        self.world_prog.destroy()
        self.shadow_prog.destroy()
        self.sun_prog.destroy()
        self.cloud_prog.destroy()

        if int(self.empty_vao) != 0:
            glDeleteVertexArrays(1, [int(self.empty_vao)])
            self.empty_vao = 0