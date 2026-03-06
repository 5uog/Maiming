# FILE: src/maiming/infrastructure/rendering/opengl/facade/renderer_backend.py
from __future__ import annotations

from pathlib import Path

import numpy as np
from OpenGL.GL import (
    glEnable,
    glDepthFunc,
    GL_DEPTH_TEST,
    GL_LESS,
)

from maiming.core.math.vec3 import Vec3
from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.state_codec import parse_state
from maiming.domain.world.chunking import ChunkKey
from maiming.infrastructure.rendering.opengl._internal.passes.cloud_pass import CloudPass
from maiming.infrastructure.rendering.opengl._internal.passes.selection_pass import SelectionPass
from maiming.infrastructure.rendering.opengl._internal.passes.shadow_map_pass import ShadowMapPass
from maiming.infrastructure.rendering.opengl._internal.passes.sun_pass import SunPass
from maiming.infrastructure.rendering.opengl._internal.passes.world_pass import WorldPass
from maiming.infrastructure.rendering.opengl._internal.pipeline.frame_pipeline import FramePipeline
from maiming.infrastructure.rendering.opengl._internal.scene.selection_outline_builder import (
    SelectionOutlineBuilder,
)
from maiming.infrastructure.rendering.opengl.facade.block_visual_resolver import BlockVisualResolver
from maiming.infrastructure.rendering.opengl.facade.gl_info_probe import GLInfoSnapshot, probe_gl_info
from maiming.infrastructure.rendering.opengl.facade.gl_renderer_params import GLRendererParams
from maiming.infrastructure.rendering.opengl.facade.gl_resources import GLResources
from maiming.infrastructure.rendering.opengl.facade.render_state import RendererRuntimeState
from maiming.infrastructure.rendering.opengl.facade.selection_controller import SelectionController

class RendererBackend:
    def __init__(
        self,
        *,
        cfg: GLRendererParams,
        state: RendererRuntimeState,
        sel_tint_strength: float = 0.55,
    ) -> None:
        self._cfg = cfg
        self._state = state
        self._sel_tint_strength = float(sel_tint_strength)

        self._res: GLResources | None = None
        self._visuals: BlockVisualResolver | None = None
        self._gl_info = GLInfoSnapshot(vendor="", renderer="", version="", glsl_version="")

        self._shadow = ShadowMapPass(self._cfg.shadow)
        self._world = WorldPass()
        self._sun = SunPass(self._cfg.sun)
        self._cloud = CloudPass(self._cfg.clouds, self._cfg.camera)
        self._selection_pass = SelectionPass()

        self._selection: SelectionController | None = None
        self._pipeline: FramePipeline | None = None

    def initialize(self, assets_dir: Path, *, block_registry: BlockRegistry) -> None:
        self._res = GLResources.load(assets_dir, blocks=block_registry)
        self._visuals = BlockVisualResolver(
            atlas=self._res.atlas,
            blocks=self._res.blocks,
        )

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        self._shadow.initialize(self._res.shadow_prog, int(self._cfg.shadow.size))
        self._world.initialize(self._res.world_prog, self._res.atlas)
        self._sun.initialize(self._res.sun_prog, int(self._res.empty_vao))
        self._cloud.initialize(self._res.cloud_prog, self._res.cloud_mesh)
        self._selection_pass.initialize(self._res.selection_prog)

        self._selection = SelectionController(
            outline_pass=self._selection_pass,
            outline_builder=SelectionOutlineBuilder(def_lookup=self._visuals.def_lookup),
            outline_enabled=bool(self._state.outline_selection_enabled),
        )

        self._pipeline = FramePipeline(
            cfg=self._cfg,
            state=self._state,
            shadow_pass=self._shadow,
            world_pass=self._world,
            sun_pass=self._sun,
            cloud_pass=self._cloud,
            selection=self._selection,
            sel_tint_strength=float(self._sel_tint_strength),
        )

        self.apply_runtime_state()
        self._gl_info = probe_gl_info()

    def destroy(self) -> None:
        self._shadow.destroy()
        self._world.destroy()
        self._selection_pass.destroy()

        if self._res is not None:
            self._res.destroy()
            self._res = None

        self._visuals = None
        self._selection = None
        self._pipeline = None
        self._gl_info = GLInfoSnapshot(vendor="", renderer="", version="", glsl_version="")

    def apply_runtime_state(self) -> None:
        self._cloud.set_wireframe(bool(self._state.cloud_wireframe))
        self._cloud.set_enabled(bool(self._state.cloud_enabled))
        self._cloud.set_density(int(self._state.cloud_density))
        self._cloud.set_seed(int(self._state.cloud_seed))

        if self._selection is not None:
            self._selection.set_outline_enabled(bool(self._state.outline_selection_enabled))

    def gl_info(self) -> tuple[str, str, str, str]:
        return (
            str(self._gl_info.vendor),
            str(self._gl_info.renderer),
            str(self._gl_info.version),
            str(self._gl_info.glsl_version),
        )

    def shadow_info(self) -> tuple[bool, int]:
        if self._pipeline is None:
            return (False, 0)
        return self._pipeline.shadow_info()

    def atlas_uv_face(self, block_state_id: str, face_idx: int) -> tuple[float, float, float, float]:
        if self._visuals is None:
            return (0.0, 0.0, 1.0, 1.0)
        return self._visuals.atlas_uv_face(str(block_state_id), int(face_idx))

    def world_build_tools(self):
        if self._visuals is None:
            return None
        return self._visuals.world_build_tools()

    def block_display_name(self, block_state_or_id: str) -> str:
        if self._visuals is None:
            base, _props = parse_state(str(block_state_or_id))
            return str(base)
        return self._visuals.display_name(str(block_state_or_id))

    def evict_chunks(self, *, keep_chunks: set[ChunkKey]) -> None:
        self._world.evict_except(keep_chunks)
        self._shadow.evict_except(keep_chunks)

    def clear_selection(self) -> None:
        if self._selection is not None:
            self._selection.clear()

    def set_selection_target(
        self,
        *,
        x: int,
        y: int,
        z: int,
        state_str: str,
        get_state,
        world_revision: int,
    ) -> None:
        if self._selection is None:
            return

        self._selection.set_target(
            x=int(x),
            y=int(y),
            z=int(z),
            state_str=str(state_str),
            get_state=get_state,
            world_revision=int(world_revision),
        )

    def submit_chunk(
        self,
        *,
        chunk_key: ChunkKey,
        world_revision: int,
        faces: list[np.ndarray],
        shadow_faces: list[np.ndarray],
    ) -> None:
        if self._res is None:
            return

        self._world.upload_chunk(
            chunk_key=chunk_key,
            world_revision=int(world_revision),
            faces=faces,
        )
        self._shadow.set_chunk_faces(
            chunk_key=chunk_key,
            world_revision=int(world_revision),
            faces=shadow_faces,
        )

    def render(
        self,
        *,
        w: int,
        h: int,
        eye: Vec3,
        yaw_deg: float,
        pitch_deg: float,
        fov_deg: float,
        render_distance_chunks: int,
    ) -> None:
        if self._pipeline is None:
            return

        self._pipeline.render(
            w=int(w),
            h=int(h),
            eye=eye,
            yaw_deg=float(yaw_deg),
            pitch_deg=float(pitch_deg),
            fov_deg=float(fov_deg),
            render_distance_chunks=int(render_distance_chunks),
        )