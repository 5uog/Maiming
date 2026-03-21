# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from OpenGL.GL import glBindVertexArray, glDepthFunc, glDepthMask, glDisable, glDrawArraysInstanced, glEnable, GL_BLEND, GL_CULL_FACE, GL_DEPTH_TEST, GL_LESS, GL_TRIANGLES

from ....features.othello.ui.special_item_art import build_special_item_icon_image
from ...math.vec3 import Vec3
from ...rendering.face_occlusion import is_local_face_occluded
from ...rendering.first_person_geometry import TexturedBox, held_block_model_boxes_for_kind
from ...rendering.player_model_pose import HeldBlockPose, PlayerModelPose
from ...rendering.uv_rects import UVRect, fence_gate_uv_rect, sub_uv_rect
from ..gl.gl_state_guard import GLStateGuard
from ..gl.mesh_buffer import MeshBuffer
from ..gl.shader_program import ShaderProgram
from ..resources.image_texture import ImageTexture
from ..resources.texture_atlas import TextureAtlas
from ..runtime.gl_renderer_params import ShadowParams
from ..runtime.render_metrics import PassFrameMetrics
from .shadow_map_pass import ShadowMapInfo
from .textured_face_pass import TexturedFacePass

def _empty_face_rows() -> tuple[np.ndarray, ...]:
    return tuple(np.zeros((0, 20), dtype=np.float32) for _ in range(6))

def _append_face_instance(buffers: list[list[list[float]]], face_idx: int, model: np.ndarray, uv_rect: UVRect) -> None:
    row = list(np.asarray(model, dtype=np.float32).reshape(16))
    row.extend([float(uv_rect[0]), float(uv_rect[1]), float(uv_rect[2]), float(uv_rect[3])])
    buffers[int(face_idx)].append(row)

def _rows_from_buffers(buffers: list[list[list[float]]]) -> tuple[np.ndarray, ...]:
    return tuple(np.asarray(face_rows, dtype=np.float32) if face_rows else np.zeros((0, 20), dtype=np.float32) for face_rows in buffers)

def _uv_rect_from_pixels(texture_uv: UVRect, px_rect: tuple[float, float, float, float]) -> UVRect:
    u0_a, v0_a, u1_a, v1_a = texture_uv
    px0, py0, px1, py1 = px_rect
    return (float(u0_a + (u1_a - u0_a) * (float(px0) / 16.0)), float(v0_a + (v1_a - v0_a) * (float(py0) / 16.0)), float(u0_a + (u1_a - u0_a) * (float(px1) / 16.0)), float(v0_a + (v1_a - v0_a) * (float(py1) / 16.0)))

def _face_uv_from_atlas(textured_box: TexturedBox, face_idx: int, texture_uv: UVRect, *, kind: str) -> UVRect:
    face_uv_pixels = textured_box.face_uv_pixels
    if face_uv_pixels is not None:
        px_rect = face_uv_pixels.get(int(face_idx))
        if px_rect is not None:
            return _uv_rect_from_pixels(texture_uv, px_rect)

    if kind == "fence_gate" and bool(textured_box.box.uv_hint):
        return fence_gate_uv_rect(texture_uv, int(face_idx), textured_box.box)
    return sub_uv_rect(texture_uv, int(face_idx), textured_box.box)

def _model_matrix_for_box(parent_transform: np.ndarray, box) -> np.ndarray:
    center_x = 0.5 * (float(box.mn_x) + float(box.mx_x))
    center_y = 0.5 * (float(box.mn_y) + float(box.mx_y))
    center_z = 0.5 * (float(box.mn_z) + float(box.mx_z))
    size_x = float(box.mx_x) - float(box.mn_x)
    size_y = float(box.mx_y) - float(box.mn_y)
    size_z = float(box.mx_z) - float(box.mn_z)
    from ...math.transform_matrices import compose_matrices, scale_matrix, translate_matrix

    return compose_matrices(parent_transform, translate_matrix(center_x, center_y, center_z), scale_matrix(size_x, size_y, size_z))

@dataclass
class PlayerModelPass:
    _face_pass: TexturedFacePass | None = None
    _shadow_prog: ShaderProgram | None = None
    _shadow_mesh: MeshBuffer | None = None
    _atlas: TextureAtlas | None = None
    _skin_texture: ImageTexture | None = None
    _uv_lookup: Callable[[str, int], UVRect] | None = None
    _special_item_textures: dict[str, ImageTexture] = field(default_factory=dict)

    def initialize(self, *, face_prog: ShaderProgram, shadow_prog: ShaderProgram, atlas: TextureAtlas, skin_texture: ImageTexture, uv_lookup: Callable[[str, int], UVRect]) -> None:
        self._face_pass = TexturedFacePass()
        self._face_pass.initialize(face_prog)
        self._shadow_prog = shadow_prog
        self._shadow_mesh = MeshBuffer.create_cube_transform_instanced()
        self._atlas = atlas
        self._skin_texture = skin_texture
        self._uv_lookup = uv_lookup
        self._special_item_textures = {"start": ImageTexture.from_image(build_special_item_icon_image("start", size=192)), "settings": ImageTexture.from_image(build_special_item_icon_image("settings", size=192))}

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
        for texture in self._special_item_textures.values():
            texture.destroy()
        self._special_item_textures.clear()

    def set_skin_texture(self, skin_texture: ImageTexture) -> None:
        self._skin_texture = skin_texture

    def _build_held_block_face_rows(self, pose: HeldBlockPose | None) -> tuple[np.ndarray, ...]:
        if pose is None or self._uv_lookup is None:
            return _empty_face_rows()

        boxes = list(held_block_model_boxes_for_kind(pose.block_kind))
        if not boxes:
            return _empty_face_rows()

        kind = "" if pose.block_kind is None else str(pose.block_kind)
        buffers: list[list[list[float]]] = [[] for _ in range(6)]
        local_boxes = [textured_box.box for textured_box in boxes]
        for textured_box in boxes:
            for face_idx in range(6):
                if is_local_face_occluded(box=textured_box.box, face_idx=int(face_idx), boxes=local_boxes):
                    continue
                texture_uv = self._uv_lookup(str(pose.block_id), int(face_idx))
                uv_rect = _face_uv_from_atlas(textured_box, int(face_idx), texture_uv, kind=kind)
                model = _model_matrix_for_box(pose.parent_transform, textured_box.box)
                _append_face_instance(buffers, int(face_idx), model, uv_rect)

        return _rows_from_buffers(buffers)

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

        self._shadow_mesh.upload_instances(rows)

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