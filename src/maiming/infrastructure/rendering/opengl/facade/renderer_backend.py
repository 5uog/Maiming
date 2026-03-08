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
from maiming.infrastructure.rendering.opengl._internal.compute.chunk_face_payload_builder import ChunkFacePayloadBuilder
from maiming.infrastructure.rendering.opengl._internal.passes.cloud_pass import CloudPass
from maiming.infrastructure.rendering.opengl._internal.passes.selection_pass import SelectionPass
from maiming.infrastructure.rendering.opengl._internal.passes.shadow_map_pass import ShadowMapPass
from maiming.infrastructure.rendering.opengl._internal.passes.sun_pass import SunPass
from maiming.infrastructure.rendering.opengl._internal.passes.world_pass import WorldPass
from maiming.infrastructure.rendering.opengl._internal.pipeline.frame_pipeline import FramePipeline
from maiming.infrastructure.rendering.opengl._internal.scene.selection_outline_builder import SelectionOutlineBuilder
from maiming.infrastructure.rendering.opengl._internal.scene.world_face_source_builder import BucketCounts
from maiming.infrastructure.rendering.opengl.facade.block_visual_resolver import BlockVisualResolver
from maiming.infrastructure.rendering.opengl.facade.gl_info_probe import GLInfoSnapshot, probe_gl_info
from maiming.infrastructure.rendering.opengl.facade.gl_renderer_params import GLRendererParams
from maiming.infrastructure.rendering.opengl.facade.gl_resources import GLResources
from maiming.infrastructure.rendering.opengl.facade.render_metrics import RendererFrameMetrics
from maiming.infrastructure.rendering.opengl.facade.render_state import RendererRuntimeState
from maiming.infrastructure.rendering.opengl.facade.selection_controller import SelectionController

def _format_context_details(info: GLInfoSnapshot) -> str:
    return (
        f"OpenGL={info.version or 'unknown'}; "
        f"GLSL={info.glsl_version or 'unknown'}; "
        f"parsed_version={int(info.major_version)}.{int(info.minor_version)}; "
        f"parsed_glsl={int(info.glsl_major_version)}.{int(info.glsl_minor_version)}; "
        f"profile={info.profile_name()}; "
        f"vendor={info.vendor or 'unknown'}; "
        f"renderer={info.renderer or 'unknown'}"
    )

def _require_gl43_core_context(info: GLInfoSnapshot) -> None:
    if not info.is_version_at_least(4, 3):
        raise RuntimeError(
            "The active context does not satisfy the OpenGL 4.3 requirement for the compute-backed "
            f"chunk face payload path. {_format_context_details(info)}"
        )

    if not info.is_core_profile():
        raise RuntimeError(
            "The active context is not Core Profile, but the renderer requires OpenGL 4.3 Core "
            f"Profile for the compute-backed chunk face payload path. {_format_context_details(info)}"
        )

    if not info.is_glsl_at_least(4, 30):
        raise RuntimeError(
            "The active GLSL version is insufficient for the compute-backed chunk face payload path. "
            f"{_format_context_details(info)}"
        )

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
        self._gl_info = GLInfoSnapshot(
            vendor="",
            renderer="",
            version="",
            glsl_version="",
            major_version=0,
            minor_version=0,
            glsl_major_version=0,
            glsl_minor_version=0,
            context_profile_mask=0,
        )

        self._shadow = ShadowMapPass(self._cfg.shadow)
        self._world = WorldPass()
        self._sun = SunPass(self._cfg.sun)
        self._cloud = CloudPass(self._cfg.clouds, self._cfg.camera)
        self._selection_pass = SelectionPass()
        self._gpu_payload_builder = ChunkFacePayloadBuilder()

        self._selection: SelectionController | None = None
        self._pipeline: FramePipeline | None = None
        self._last_payload_validation: object | None = None
        self._last_frame_metrics = RendererFrameMetrics()

    def initialize(self, assets_dir: Path, *, block_registry: BlockRegistry) -> None:
        self._gl_info = probe_gl_info()
        _require_gl43_core_context(self._gl_info)

        try:
            self._res = GLResources.load(assets_dir, blocks=block_registry)
        except Exception as exc:
            raise RuntimeError(
                "OpenGL 4.3 initialization failed while compiling or linking one or more required "
                "shader resources for the renderer, including the compute-backed chunk face payload "
                f"program. {_format_context_details(self._gl_info)}\n"
                f"Original error:\n{exc}"
            ) from exc

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
        self._gpu_payload_builder.initialize(self._res.chunk_face_payload_prog)

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

    def destroy(self) -> None:
        self._gpu_payload_builder.destroy()
        self._shadow.destroy()
        self._world.destroy()
        self._selection_pass.destroy()

        if self._res is not None:
            self._res.destroy()
            self._res = None

        self._visuals = None
        self._selection = None
        self._pipeline = None
        self._last_payload_validation = None
        self._last_frame_metrics = RendererFrameMetrics()
        self._gl_info = GLInfoSnapshot(
            vendor="",
            renderer="",
            version="",
            glsl_version="",
            major_version=0,
            minor_version=0,
            glsl_major_version=0,
            glsl_minor_version=0,
            context_profile_mask=0,
        )

    def apply_runtime_state(self) -> None:
        self._cloud.set_wireframe(bool(self._state.cloud_wireframe))
        self._cloud.set_enabled(bool(self._state.cloud_enabled))
        self._cloud.set_density(int(self._state.cloud_density))
        self._cloud.set_seed(int(self._state.cloud_seed))
        self._cloud.set_flow_direction(str(self._state.cloud_flow_direction))

        if self._selection is not None:
            self._selection.set_outline_enabled(bool(self._state.outline_selection_enabled))

    def set_cloud_motion_paused(self, on: bool) -> None:
        self._cloud.set_motion_paused(bool(on))

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

    def payload_validation_report(self) -> object | None:
        return self._last_payload_validation

    def frame_metrics(self) -> RendererFrameMetrics:
        return self._last_frame_metrics

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
        self._gpu_payload_builder.evict_except(keep_chunks)

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
        faces: list[np.ndarray] | None = None,
        shadow_faces: list[np.ndarray] | None = None,
        gpu_face_sources: np.ndarray | None = None,
        gpu_bucket_counts: BucketCounts | None = None,
    ) -> None:
        if self._res is None:
            return

        authoritative_world_faces: list[np.ndarray] | None = None
        authoritative_shadow_faces: list[np.ndarray] | None = None

        if gpu_face_sources is not None and gpu_bucket_counts is not None:
            gpu_payload = self._gpu_payload_builder.build_and_store(
                chunk_key=chunk_key,
                world_revision=int(world_revision),
                face_sources=gpu_face_sources,
                bucket_counts=gpu_bucket_counts,
            )
            authoritative_world_faces = gpu_payload.face_buckets
            authoritative_shadow_faces = authoritative_world_faces
            self._last_payload_validation = None
        else:
            if faces is None:
                return
            authoritative_world_faces = faces
            authoritative_shadow_faces = shadow_faces if shadow_faces is not None else faces
            self._last_payload_validation = None

        self._world.upload_chunk(
            chunk_key=chunk_key,
            world_revision=int(world_revision),
            faces=authoritative_world_faces,
        )
        self._shadow.set_chunk_faces(
            chunk_key=chunk_key,
            world_revision=int(world_revision),
            faces=authoritative_shadow_faces,
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
            self._last_frame_metrics = RendererFrameMetrics()
            return

        self._last_frame_metrics = self._pipeline.render(
            w=int(w),
            h=int(h),
            eye=eye,
            yaw_deg=float(yaw_deg),
            pitch_deg=float(pitch_deg),
            fov_deg=float(fov_deg),
            render_distance_chunks=int(render_distance_chunks),
        )