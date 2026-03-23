# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from OpenGL.GL import glBindVertexArray, glDepthFunc, glDepthMask, glDisable, glDrawArraysInstanced, glEnable, GL_BLEND, GL_CULL_FACE, GL_DEPTH_TEST, GL_LESS, GL_TRIANGLES

from ....features.othello.ui.special_item_art import build_special_item_icon_image
from ...math.vec3 import Vec3
from ...rendering.face_occlusion import is_local_face_occluded
from ...rendering.face_row_utils import append_face_instance, atlas_face_uv, empty_textured_face_rows, face_rows_from_buffers, model_matrix_for_local_box
from ...rendering.first_person_geometry import held_block_model_boxes_for_kind
from ...rendering.player_model_pose import HeldBlockPose, PlayerModelPose
from ...rendering.uv_rects import UVRect
from ..gl.gl_state_guard import GLStateGuard
from ..gl.mesh_buffer import MeshBuffer
from ..gl.shader_program import ShaderProgram
from ..resources.image_texture import ImageTexture
from ..resources.texture_atlas import TextureAtlas
from ..runtime.gl_renderer_params import ShadowParams
from ..runtime.render_metrics import PassFrameMetrics
from .shadow_map_pass import ShadowMapInfo
from .textured_face_pass import TexturedFacePass

@dataclass
class PlayerModelPass:
    _face_pass: TexturedFacePass | None = None
    _shadow_prog: ShaderProgram | None = None
    _shadow_mesh: MeshBuffer | None = None
    _atlas: TextureAtlas | None = None
    _skin_texture: ImageTexture | None = None
    _uv_lookup: Callable[[str, int], UVRect] | None = None
    _special_item_textures: dict[str, ImageTexture] = field(default_factory=dict)
    _shadow_upload_key: tuple[object, ...] | None = None

    def initialize(self, *, face_prog: ShaderProgram, shadow_prog: ShaderProgram, atlas: TextureAtlas, skin_texture: ImageTexture, uv_lookup: Callable[[str, int], UVRect]) -> None:
        self._face_pass = TexturedFacePass()
        self._face_pass.initialize(face_prog)
        self._shadow_prog = shadow_prog
        self._shadow_mesh = MeshBuffer.create_cube_transform_instanced()
        self._atlas = atlas
        self._skin_texture = skin_texture
        self._uv_lookup = uv_lookup
        self._special_item_textures = {"start": ImageTexture.from_image(build_special_item_icon_image("start", size=192)), "settings": ImageTexture.from_image(build_special_item_icon_image("settings", size=192))}
        self._shadow_upload_key = None

    def destroy(self) -> None:
        if self._face_pass is not None:
            self._face_pass.destroy()
        self._face_pass = None
        if self._shadow_mesh is not None:
            self._shadow_mesh.destroy()
        self._shadow_mesh = None
        self._shadow_prog = None
        self._atlas = None
        self._skin_texture = None
        self._uv_lookup = None
        self._shadow_upload_key = None
        for texture in self._special_item_textures.values():
            texture.destroy()
        self._special_item_textures.clear()

    def set_skin_texture(self, skin_texture: ImageTexture) -> None:
        self._skin_texture = skin_texture

    def _build_held_block_face_rows(self, pose: HeldBlockPose | None) -> tuple[np.ndarray, ...]:
        if pose is None or self._uv_lookup is None:
            return empty_textured_face_rows()

        boxes = list(held_block_model_boxes_for_kind(pose.block_kind))
        if not boxes:
            return empty_textured_face_rows()

        kind = "" if pose.block_kind is None else str(pose.block_kind)
        buffers: list[list[list[float]]] = [[] for _ in range(6)]
        local_boxes = [textured_box.box for textured_box in boxes]
        for textured_box in boxes:
            for face_idx in range(6):
                if is_local_face_occluded(box=textured_box.box, face_idx=int(face_idx), boxes=local_boxes):
                    continue
                texture_uv = self._uv_lookup(str(pose.block_id), int(face_idx))
                uv_rect = atlas_face_uv(texture_uv, int(face_idx), textured_box.box, kind=kind, face_uv_pixels=textured_box.face_uv_pixels)
                model = model_matrix_for_local_box(pose.parent_transform, textured_box.box)
                append_face_instance(buffers, int(face_idx), model, uv_rect)

        return face_rows_from_buffers(buffers)

    def draw_world(self, *, pose: PlayerModelPose, view_proj: np.ndarray, light_view_proj: np.ndarray, sun_dir: Vec3, debug_shadow: bool, shadow_enabled: bool, shadow: ShadowParams, shadow_info: ShadowMapInfo) -> tuple[int, int]:
        del light_view_proj, debug_shadow, shadow_enabled, shadow, shadow_info
        if self._face_pass is None or self._skin_texture is None or self._atlas is None:
            return (0, 0)

        draw_calls = 0
        instances = 0

        dc, inst = self._face_pass.draw(face_rows=pose.skin_face_rows, view_proj=view_proj, tex_id=int(self._skin_texture.tex_id), sun_dir=sun_dir)
        draw_calls += int(dc)
        instances += int(inst)

        held_block_rows = self._build_held_block_face_rows(pose.held_block_pose)
        dc, inst = self._face_pass.draw(face_rows=held_block_rows, view_proj=view_proj, tex_id=int(self._atlas.tex_id), sun_dir=sun_dir)
        draw_calls += int(dc)
        instances += int(inst)

        icon_key = None if pose.visible_special_item_icon is None else str(pose.visible_special_item_icon)
        icon_texture = None if icon_key is None else self._special_item_textures.get(icon_key)
        if icon_texture is not None:
            dc, inst = self._face_pass.draw(face_rows=pose.special_item_face_rows, view_proj=view_proj, tex_id=int(icon_texture.tex_id), sun_dir=sun_dir)
            draw_calls += int(dc)
            instances += int(inst)

        return (int(draw_calls), int(instances))

    def draw_shadow(self, *, pose: PlayerModelPose, light_view_proj: np.ndarray) -> tuple[int, int]:
        if self._shadow_prog is None or self._shadow_mesh is None:
            return (0, 0)

        rows = pose.shadow_rows
        if rows.size <= 0 or int(rows.shape[0]) <= 0:
            return (0, 0)

        shadow_upload_key = (id(rows), int(rows.shape[0]))
        if self._shadow_upload_key != shadow_upload_key:
            self._shadow_mesh.upload_instances(rows)
            self._shadow_upload_key = shadow_upload_key

        with GLStateGuard(capture_framebuffer=False, capture_viewport=False, capture_enables=(GL_BLEND, GL_DEPTH_TEST, GL_CULL_FACE), capture_cull_mode=False, capture_polygon_mode=False):
            glDisable(GL_BLEND)
            glDisable(GL_CULL_FACE)

            glEnable(GL_DEPTH_TEST)
            glDepthMask(True)
            glDepthFunc(GL_LESS)

            self._shadow_prog.use()
            self._shadow_prog.set_mat4("u_lightViewProj", light_view_proj.astype(np.float32, copy=False))

            glBindVertexArray(int(self._shadow_mesh.vao))
            glDrawArraysInstanced(GL_TRIANGLES, 0, int(self._shadow_mesh.vertex_count), int(rows.shape[0]))
            glBindVertexArray(0)

        return (1, int(rows.shape[0]))

    def world_metrics(self, *, pose: PlayerModelPose, view_proj: np.ndarray, light_view_proj: np.ndarray, sun_dir: Vec3, debug_shadow: bool, shadow_enabled: bool, shadow: ShadowParams, shadow_info: ShadowMapInfo) -> PassFrameMetrics:
        dc, inst = self.draw_world(pose=pose, view_proj=view_proj, light_view_proj=light_view_proj, sun_dir=sun_dir, debug_shadow=bool(debug_shadow), shadow_enabled=bool(shadow_enabled), shadow=shadow, shadow_info=shadow_info)
        return PassFrameMetrics(cpu_ms=0.0, draw_calls=int(dc), instances=int(inst), rendered=bool(dc > 0))
