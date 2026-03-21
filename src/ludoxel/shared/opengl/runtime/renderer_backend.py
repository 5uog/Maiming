# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import time
import numpy as np

from PyQt6.QtGui import QImage
from OpenGL.GL import glBindFramebuffer, glBindRenderbuffer, glBindTexture, glCheckFramebufferStatus, glClear, glClearColor, glDeleteFramebuffers, glDeleteRenderbuffers, glDeleteTextures, glDepthFunc, glDisable, glEnable, glFramebufferRenderbuffer, glFramebufferTexture2D, glGenFramebuffers, glGenRenderbuffers, glGenTextures, glReadPixels, glRenderbufferStorage, glTexImage2D, glTexParameteri, glViewport, GL_BLEND, GL_CLAMP_TO_EDGE, GL_COLOR_ATTACHMENT0, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, GL_DEPTH_ATTACHMENT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_COMPONENT24, GL_DEPTH_TEST, GL_FRAMEBUFFER, GL_FRAMEBUFFER_COMPLETE, GL_LESS, GL_LINEAR, GL_RENDERBUFFER, GL_RGBA, GL_RGBA8, GL_SCISSOR_TEST, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_UNSIGNED_BYTE

from ....application.runtime.state.render_snapshot import FallingBlockRenderSampleDTO
from ...math import mat4
from ...math.vec3 import Vec3
from ...blocks.registry.block_registry import BlockRegistry
from ...blocks.state.state_codec import parse_state
from ...math.chunking.chunk_grid import ChunkKey
from ..gl.gl_state_guard import GLStateGuard
from ..compute.chunk_face_payload_builder import ChunkFacePayloadBuilder
from ..passes.cloud_pass import CloudPass
from ..passes.falling_block_pass import FallingBlockPass
from ..passes.first_person_arm_pass import FirstPersonArmPass
from ..passes.held_block_pass import HeldBlockPass
from ..passes.special_item_pass import SpecialItemPass
from ....features.othello.opengl.othello_pass import OthelloPass
from ..passes.player_model_pass import PlayerModelPass
from ..passes.selection_pass import SelectionPass
from ..passes.shadow_map_pass import ShadowMapPass
from ..passes.sun_pass import SunPass
from ..passes.world_pass import WorldPass
from ..pipeline.frame_pipeline import FramePipeline
from ...rendering.selection_outline_builder import SelectionOutlineBuilder
from ...rendering.face_bucket_layout import BucketCounts
from .gl_info_probe import GLInfoSnapshot, probe_gl_info
from .gl_renderer_params import GLRendererParams
from .gl_resources import GLResources
from ....features.othello.application.rendering.othello_render_state import OthelloRenderState
from ...rendering.player_model_pose import build_player_model_pose
from ...rendering.player_render_state import PlayerRenderState
from .render_metrics import RendererFrameMetrics
from .render_state import RendererRuntimeState
from .block_visual_resolver import BlockVisualResolver
from .selection_controller import SelectionController
from .texture_animation_controller import TextureAnimationController

_PREVIEW_EYE = Vec3(0.0, 0.98, 6.8)
_PREVIEW_TARGET = Vec3(0.0, 0.78, 0.0)
_PREVIEW_FOV_DEG = 26.0
_PREVIEW_NEAR = 0.1
_PREVIEW_FAR = 10.0

def _format_context_details(info: GLInfoSnapshot) -> str:
    return (f"OpenGL={info.version or 'unknown'}; GLSL={info.glsl_version or 'unknown'}; parsed_version={int(info.major_version)}.{int(info.minor_version)}; parsed_glsl={int(info.glsl_major_version)}.{int(info.glsl_minor_version)}; profile={info.profile_name()}; vendor={info.vendor or 'unknown'}; renderer={info.renderer or 'unknown'}")

def _require_gl43_core_context(info: GLInfoSnapshot) -> None:
    if not info.is_version_at_least(4, 3):
        raise RuntimeError(f"The active context does not satisfy the OpenGL 4.3 requirement for the compute-backed chunk face payload path. {_format_context_details(info)}")

    if not info.is_core_profile():
        raise RuntimeError(f"The active context is not Core Profile, but the renderer requires OpenGL 4.3 Core Profile for the compute-backed chunk face payload path. {_format_context_details(info)}")

    if not info.is_glsl_at_least(4, 30):
        raise RuntimeError(f"The active GLSL version is insufficient for the compute-backed chunk face payload path. {_format_context_details(info)}")

class RendererBackend:
    def __init__(self, *, cfg: GLRendererParams, state: RendererRuntimeState, sel_tint_strength: float=0.55) -> None:
        self._cfg = cfg
        self._state = state
        self._sel_tint_strength = float(sel_tint_strength)

        self._res: GLResources | None = None
        self._visuals: BlockVisualResolver | None = None
        self._gl_info = GLInfoSnapshot(vendor="", renderer="", version="", glsl_version="", major_version=0, minor_version=0, glsl_major_version=0, glsl_minor_version=0, context_profile_mask=0)

        self._shadow = ShadowMapPass(self._cfg.shadow)
        self._world = WorldPass()
        self._falling_blocks = FallingBlockPass()
        self._player = PlayerModelPass()
        self._first_person_arm = FirstPersonArmPass()
        self._held_block = HeldBlockPass()
        self._special_item = SpecialItemPass()
        self._sun = SunPass(self._cfg.sun)
        self._cloud = CloudPass(self._cfg.clouds, self._cfg.camera)
        self._othello = OthelloPass()
        self._selection_pass = SelectionPass()
        self._gpu_payload_builder = ChunkFacePayloadBuilder()

        self._selection: SelectionController | None = None
        self._pipeline: FramePipeline | None = None
        self._texture_animations: TextureAnimationController | None = None
        self._last_payload_validation: object | None = None
        self._last_frame_metrics = RendererFrameMetrics()
        self._preview_fbo: int = 0
        self._preview_color_tex: int = 0
        self._preview_depth_rbo: int = 0
        self._preview_width: int = 0
        self._preview_height: int = 0

    def initialize(self, assets_dir: Path, *, block_registry: BlockRegistry) -> None:
        self._gl_info = probe_gl_info()
        _require_gl43_core_context(self._gl_info)

        try:
            self._res = GLResources.load(assets_dir, blocks=block_registry)
        except Exception as exc:
            raise RuntimeError(f"OpenGL 4.3 initialization failed while compiling or linking one or more required shader resources for the renderer, including the compute-backed chunk face payload program. {_format_context_details(self._gl_info)}\nOriginal error:\n{exc}") from exc

        self._visuals = BlockVisualResolver(atlas=self._res.atlas, blocks=self._res.blocks)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        self._shadow.initialize(self._res.shadow_prog, int(self._cfg.shadow.size))
        self._world.initialize(shadowed_prog=self._res.world_prog, no_shadow_prog=self._res.world_no_shadow_prog, atlas=self._res.atlas)
        self._falling_blocks.initialize(prog=self._res.first_person_face_prog, atlas=self._res.atlas, uv_lookup=self._visuals.atlas_uv_face, def_lookup=self._visuals.def_lookup)
        self._player.initialize(face_prog=self._res.first_person_face_prog, shadow_prog=self._res.player_model_shadow_prog, atlas=self._res.atlas, skin_texture=self._res.skin_texture, uv_lookup=self._visuals.atlas_uv_face)
        self._first_person_arm.initialize(prog=self._res.first_person_face_prog, skin_texture=self._res.skin_texture)
        self._held_block.initialize(prog=self._res.first_person_face_prog, atlas=self._res.atlas, uv_lookup=self._visuals.atlas_uv_face, def_lookup=self._visuals.def_lookup)
        self._special_item.initialize(prog=self._res.first_person_face_prog)
        self._sun.initialize(self._res.sun_prog, int(self._res.empty_vao))
        self._cloud.initialize(self._res.cloud_prog, self._res.cloud_mesh)
        self._othello.initialize(world_prog=self._res.othello_prog, shadow_prog=self._res.othello_shadow_prog)
        self._selection_pass.initialize(self._res.selection_prog)
        self._gpu_payload_builder.initialize(self._res.chunk_face_payload_prog)

        self._selection = SelectionController(outline_pass=self._selection_pass, outline_builder=SelectionOutlineBuilder(def_lookup=self._visuals.def_lookup), outline_enabled=bool(self._state.outline_selection_enabled))
        self._pipeline = FramePipeline(cfg=self._cfg, state=self._state, shadow_pass=self._shadow, world_pass=self._world, falling_block_pass=self._falling_blocks, player_pass=self._player, first_person_arm_pass=self._first_person_arm, held_block_pass=self._held_block, special_item_pass=self._special_item, sun_pass=self._sun, cloud_pass=self._cloud, othello_pass=self._othello, selection=self._selection, sel_tint_strength=float(self._sel_tint_strength))
        self._texture_animations = TextureAnimationController(block_dir=Path(assets_dir) / "minecraft" / "textures" / "block", atlas=self._res.atlas)

        self.apply_runtime_state()

    def destroy(self) -> None:
        self._gpu_payload_builder.destroy()
        self._shadow.destroy()
        self._world.destroy()
        self._falling_blocks.destroy()
        self._player.destroy()
        self._first_person_arm.destroy()
        self._held_block.destroy()
        self._special_item.destroy()
        self._othello.destroy()
        self._selection_pass.destroy()
        self._destroy_preview_target()

        if self._res is not None:
            self._res.destroy()
            self._res = None

        self._visuals = None
        self._selection = None
        self._pipeline = None
        self._texture_animations = None
        self._last_payload_validation = None
        self._last_frame_metrics = RendererFrameMetrics()
        self._gl_info = GLInfoSnapshot(vendor="", renderer="", version="", glsl_version="", major_version=0, minor_version=0, glsl_major_version=0, glsl_minor_version=0, context_profile_mask=0)

    def apply_runtime_state(self) -> None:
        self._cloud.set_wireframe(bool(self._state.cloud_wireframe))
        self._cloud.set_enabled(bool(self._state.cloud_enabled))
        self._cloud.set_density(int(self._state.cloud_density))
        self._cloud.set_seed(int(self._state.cloud_seed))
        self._cloud.set_flow_direction(str(self._state.cloud_flow_direction))
        if self._texture_animations is not None:
            self._texture_animations.set_enabled(bool(self._state.animated_textures_enabled))

        if self._selection is not None:
            self._selection.set_outline_enabled(bool(self._state.outline_selection_enabled))

    def set_cloud_motion_paused(self, on: bool) -> None:
        self._cloud.set_motion_paused(bool(on))

    def set_texture_animation_paused(self, on: bool) -> None:
        if self._texture_animations is not None:
            self._texture_animations.set_paused(bool(on), elapsed_s=time.perf_counter())

    def gl_info(self) -> tuple[str, str, str, str]:
        return (str(self._gl_info.vendor), str(self._gl_info.renderer), str(self._gl_info.version), str(self._gl_info.glsl_version))

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

    def set_selection_target(self, *, x: int, y: int, z: int, state_str: str, get_state, world_revision: int) -> None:
        if self._selection is None:
            return

        self._selection.set_target(x=int(x), y=int(y), z=int(z), state_str=str(state_str), get_state=get_state, world_revision=int(world_revision))

    def submit_chunk(self, *, chunk_key: ChunkKey, world_revision: int, faces: list[np.ndarray] | None=None, shadow_faces: list[np.ndarray] | None=None, gpu_face_sources: np.ndarray | None=None, gpu_bucket_counts: BucketCounts | None=None) -> None:
        if self._res is None:
            return

        authoritative_world_faces: list[np.ndarray] | None = None
        authoritative_shadow_faces: list[np.ndarray] | None = None

        if gpu_face_sources is not None and gpu_bucket_counts is not None:
            gpu_payload = self._gpu_payload_builder.build_and_store(chunk_key=chunk_key, world_revision=int(world_revision), face_sources=gpu_face_sources, bucket_counts=gpu_bucket_counts)
            authoritative_world_faces = gpu_payload.face_buckets
            authoritative_shadow_faces = authoritative_world_faces
            self._last_payload_validation = None
        else:
            if faces is None:
                return
            authoritative_world_faces = faces
            authoritative_shadow_faces = shadow_faces if shadow_faces is not None else faces
            self._last_payload_validation = None

        self._world.upload_chunk(chunk_key=chunk_key, world_revision=int(world_revision), faces=authoritative_world_faces)
        self._shadow.set_chunk_faces(chunk_key=chunk_key, world_revision=int(world_revision), faces=authoritative_shadow_faces)

    def render(self, *, w: int, h: int, eye: Vec3, yaw_deg: float, pitch_deg: float, roll_deg: float=0.0, fov_deg: float, render_distance_chunks: int, player_state: PlayerRenderState | None=None, othello_state: OthelloRenderState | None=None, falling_blocks: tuple[FallingBlockRenderSampleDTO, ...] = ()) -> None:
        if self._pipeline is None:
            self._last_frame_metrics = RendererFrameMetrics()
            return
        if self._texture_animations is not None:
            self._texture_animations.update(time.perf_counter())

        self._last_frame_metrics = self._pipeline.render(w=int(w), h=int(h), eye=eye, yaw_deg=float(yaw_deg), pitch_deg=float(pitch_deg), roll_deg=float(roll_deg), fov_deg=float(fov_deg), render_distance_chunks=int(render_distance_chunks), player_state=player_state, othello_state=othello_state, falling_blocks=falling_blocks)

    def set_player_skin_image(self, image: QImage) -> None:
        if self._res is None:
            return
        skin_texture = self._res.replace_skin_texture(image)
        self._player.set_skin_texture(skin_texture)
        self._first_person_arm.set_skin_texture(skin_texture)

    def render_player_preview_frame(self, *, width: int, height: int, player_state: PlayerRenderState | None, restore_framebuffer: int, restore_viewport: tuple[int, int, int, int], device_pixel_ratio: float=1.0) -> QImage:
        if self._res is None or self._player is None or player_state is None:
            return QImage()
        target_width = max(1, int(width))
        target_height = max(1, int(height))
        if not bool(self._ensure_preview_target(target_width, target_height)):
            return QImage()
        pose = build_player_model_pose(player_state)
        aspect = float(target_width) / max(1.0, float(target_height))
        view = mat4.look_dir(_PREVIEW_EYE, (_PREVIEW_TARGET - _PREVIEW_EYE).normalized())
        proj = mat4.perspective(float(_PREVIEW_FOV_DEG), float(aspect), float(_PREVIEW_NEAR), float(_PREVIEW_FAR))
        view_proj = mat4.mul(proj, view)

        frame_bytes = None
        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE, GL_SCISSOR_TEST), capture_cull_mode=True, capture_polygon_mode=False):
            try:
                glBindFramebuffer(GL_FRAMEBUFFER, int(self._preview_fbo))
                glDisable(GL_SCISSOR_TEST)
                glViewport(0, 0, int(target_width), int(target_height))
                glClearColor(0.0, 0.0, 0.0, 0.0)
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                self._player.draw_world(pose=pose, view_proj=view_proj, light_view_proj=mat4.identity(), sun_dir=self._state.sun_dir, debug_shadow=False, shadow_enabled=False, shadow=self._cfg.shadow, shadow_info=self._shadow.info())
                frame_bytes = glReadPixels(0, 0, int(target_width), int(target_height), GL_RGBA, GL_UNSIGNED_BYTE)
            finally:
                glBindFramebuffer(GL_FRAMEBUFFER, int(restore_framebuffer))
                restore_x, restore_y, restore_w, restore_h = restore_viewport
                glViewport(int(restore_x), int(restore_y), int(restore_w), int(restore_h))
        if frame_bytes is None:
            return QImage()
        image = QImage(frame_bytes, int(target_width), int(target_height), QImage.Format.Format_RGBA8888).mirrored(False, True).copy()
        image.setDevicePixelRatio(max(1.0, float(device_pixel_ratio)))
        return image

    def _destroy_preview_target(self) -> None:
        if int(self._preview_depth_rbo) != 0:
            glDeleteRenderbuffers(1, [int(self._preview_depth_rbo)])
            self._preview_depth_rbo = 0
        if int(self._preview_color_tex) != 0:
            glDeleteTextures(1, [int(self._preview_color_tex)])
            self._preview_color_tex = 0
        if int(self._preview_fbo) != 0:
            glDeleteFramebuffers(1, [int(self._preview_fbo)])
            self._preview_fbo = 0
        self._preview_width = 0
        self._preview_height = 0

    def _ensure_preview_target(self, width: int, height: int) -> bool:
        target_width = max(1, int(width))
        target_height = max(1, int(height))
        if int(self._preview_fbo) != 0 and int(self._preview_color_tex) != 0 and int(self._preview_depth_rbo) != 0 and int(self._preview_width) == int(target_width) and int(self._preview_height) == int(target_height):
            return True

        self._destroy_preview_target()

        color_tex = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, int(color_tex))
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, int(target_width), int(target_height), 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)

        depth_rbo = int(glGenRenderbuffers(1))
        glBindRenderbuffer(GL_RENDERBUFFER, int(depth_rbo))
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, int(target_width), int(target_height))
        glBindRenderbuffer(GL_RENDERBUFFER, 0)

        fbo = int(glGenFramebuffers(1))
        glBindFramebuffer(GL_FRAMEBUFFER, int(fbo))
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, int(color_tex), 0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, int(depth_rbo))
        status = int(glCheckFramebufferStatus(GL_FRAMEBUFFER))
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        if status != int(GL_FRAMEBUFFER_COMPLETE):
            glDeleteRenderbuffers(1, [int(depth_rbo)])
            glDeleteTextures(1, [int(color_tex)])
            glDeleteFramebuffers(1, [int(fbo)])
            return False

        self._preview_fbo = int(fbo)
        self._preview_color_tex = int(color_tex)
        self._preview_depth_rbo = int(depth_rbo)
        self._preview_width = int(target_width)
        self._preview_height = int(target_height)
        return True