# FILE: src/maiming/infrastructure/rendering/opengl/_internal/scene/first_person_geometry.py
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Callable, Sequence

import numpy as np

from ......core.grid.face_index import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from ......domain.blocks.block_definition import BlockDefinition
from ......domain.blocks.models.common import LocalBox
from ......domain.blocks.models.dimensions import px_box
from ......domain.blocks.models.fence_gate import boxes_for_fence_gate
from ......domain.blocks.models.slab import boxes_for_slab
from ......domain.blocks.models.stairs import boxes_for_stairs
from .face_occlusion import is_local_face_occluded
from ...facade.player_render_state import FirstPersonRenderState

UVRect = tuple[float, float, float, float]
DefLookup = Callable[[str], BlockDefinition | None]
UVLookup = Callable[[str, int], UVRect]

_PX = 1.0 / 16.0
FIRST_PERSON_HAND_NEAR = 0.05
FIRST_PERSON_ARM_HAND_ANCHOR = (0.0, -12.0 * _PX, 0.0)
THIRD_PERSON_RIGHT_HAND_ANCHOR = (0.0, -10.5 * _PX, 0.0)

_ITEM_POS_X = 0.9
_ITEM_POS_Y = -0.45
_ITEM_POS_Z = -1.05
_ITEM_SWING_X_POS_SCALE = -0.25
_ITEM_SWING_Y_POS_SCALE = 0.12
_ITEM_SWING_Z_POS_SCALE = -0.18
_ITEM_PRESWING_ROT_Y_DEG = 45.0
_ITEM_SWING_Y_ROT_AMOUNT_DEG = 20.0
_ITEM_SWING_Z_ROT_AMOUNT_DEG = 20.0
_ITEM_SWING_X_ROT_AMOUNT_DEG = -80.0

_ARM_POS_X = 1.5
_ARM_POS_Y = -1.05
_ARM_POS_Z = -1.0
_ARM_SWING_X_POS_SCALE = -0.18
_ARM_SWING_Y_POS_SCALE = 0.12
_ARM_SWING_Z_POS_SCALE = -0.16
_ARM_PRESWING_ROT_Y_DEG = 45.0
_ARM_SWING_Y_ROT_AMOUNT_DEG = -50.0
_ARM_SWING_Z_ROT_AMOUNT_DEG = 12.0
_ARM_PREROTATION_X_OFFSET_PX = -1.0
_ARM_PREROTATION_Y_OFFSET_PX = 3.6
_ARM_PREROTATION_Z_OFFSET_PX = 3.5
_ARM_ROT_Z_DEG = 60.0
_ARM_ROT_X_DEG = 140.0
_ARM_ROT_Y_DEG = -60.0
_ARM_POSTROTATION_X_OFFSET_PX = 5.6

_BLOCK_FIRSTPERSON_TRANSLATE_PX = (0.0, 2.5, 0.0)
_BLOCK_FIRSTPERSON_ROTATE_DEG = (0.0, 45.0, 0.0)
_BLOCK_FIRSTPERSON_SCALE = (0.4, 0.4, 0.4)
_BLOCK_THIRDPERSON_TRANSLATE_PX = (0.0, 2.5, 0.0)
_BLOCK_THIRDPERSON_ROTATE_DEG = (75.0, 45.0, 0.0)
_BLOCK_THIRDPERSON_SCALE = (0.375, 0.375, 0.375)

_ARM_BASE_BOX = LocalBox(-1.5 * _PX, -12.0 * _PX, -2.0 * _PX, 1.5 * _PX, 0.0, 2.0 * _PX)
_ARM_SLEEVE_BOX = LocalBox(-(1.5 + 0.25) * _PX, -(12.0 + 0.25) * _PX, -(2.0 + 0.25) * _PX, (1.5 + 0.25) * _PX, 0.25 * _PX, (2.0 + 0.25) * _PX)

@dataclass(frozen=True)
class TexturedBox:
    box: LocalBox
    face_uv_pixels: dict[int, tuple[float, float, float, float]] | None = None

_FENCE_INVENTORY_BOXES: tuple[TexturedBox, ...] = (
    TexturedBox(box=px_box(6, 0, 6, 10, 16, 10), face_uv_pixels={FACE_POS_X: (10.0, 0.0, 14.0, 16.0), FACE_NEG_X: (6.0, 0.0, 10.0, 16.0), FACE_POS_Y: (6.0, 6.0, 10.0, 10.0), FACE_NEG_Y: (10.0, 6.0, 14.0, 10.0), FACE_POS_Z: (6.0, 0.0, 10.0, 16.0), FACE_NEG_Z: (14.0, 0.0, 10.0, 16.0)}),
    TexturedBox(box=px_box(7, 6, -2, 9, 9, 18), face_uv_pixels={FACE_POS_X: (9.0, 6.0, 11.0, 9.0), FACE_NEG_X: (7.0, 6.0, 9.0, 9.0), FACE_POS_Y: (7.0, 0.0, 9.0, 4.0), FACE_NEG_Y: (9.0, 0.0, 11.0, 4.0), FACE_POS_Z: (7.0, 4.0, 9.0, 7.0), FACE_NEG_Z: (11.0, 4.0, 13.0, 7.0)}),
    TexturedBox(box=px_box(7, 12, -2, 9, 15, 18), face_uv_pixels={FACE_POS_X: (9.0, 12.0, 11.0, 15.0), FACE_NEG_X: (7.0, 12.0, 9.0, 15.0), FACE_POS_Y: (7.0, 7.0, 9.0, 11.0), FACE_NEG_Y: (9.0, 7.0, 11.0, 11.0), FACE_POS_Z: (7.0, 9.0, 9.0, 12.0), FACE_NEG_Z: (11.0, 9.0, 13.0, 12.0)}),
)

_ALEX_RIGHT_ARM_BASE_UV_PX = {FACE_POS_X: (40.0, 20.0, 44.0, 32.0), FACE_NEG_X: (47.0, 20.0, 51.0, 32.0), FACE_POS_Y: (44.0, 16.0, 47.0, 20.0), FACE_NEG_Y: (47.0, 16.0, 50.0, 20.0), FACE_POS_Z: (44.0, 20.0, 47.0, 32.0), FACE_NEG_Z: (51.0, 20.0, 54.0, 32.0)}
_ALEX_RIGHT_ARM_SLEEVE_UV_PX = {FACE_POS_X: (40.0, 36.0, 44.0, 48.0), FACE_NEG_X: (47.0, 36.0, 51.0, 48.0), FACE_POS_Y: (44.0, 32.0, 47.0, 36.0), FACE_NEG_Y: (47.0, 32.0, 50.0, 36.0), FACE_POS_Z: (44.0, 36.0, 47.0, 48.0), FACE_NEG_Z: (51.0, 36.0, 54.0, 48.0)}

def _clampf(x: float, lo: float, hi: float) -> float:
    value = float(x)
    if value < float(lo):
        return float(lo)
    if value > float(hi):
        return float(hi)
    return float(value)

def _mat_identity() -> np.ndarray:
    return np.identity(4, dtype=np.float32)

def _mat_translate(x: float, y: float, z: float) -> np.ndarray:
    mat = _mat_identity()
    mat[0, 3] = float(x)
    mat[1, 3] = float(y)
    mat[2, 3] = float(z)
    return mat

def _mat_scale(x: float, y: float, z: float) -> np.ndarray:
    mat = _mat_identity()
    mat[0, 0] = float(x)
    mat[1, 1] = float(y)
    mat[2, 2] = float(z)
    return mat

def _mat_rot_x_deg(deg: float) -> np.ndarray:
    rad = math.radians(float(deg))
    mat = _mat_identity()
    c = math.cos(rad)
    s = math.sin(rad)
    mat[1, 1] = float(c)
    mat[1, 2] = float(-s)
    mat[2, 1] = float(s)
    mat[2, 2] = float(c)
    return mat

def _mat_rot_y_deg(deg: float) -> np.ndarray:
    rad = math.radians(float(deg))
    mat = _mat_identity()
    c = math.cos(rad)
    s = math.sin(rad)
    mat[0, 0] = float(c)
    mat[0, 2] = float(-s)
    mat[2, 0] = float(s)
    mat[2, 2] = float(c)
    return mat

def _mat_rot_z_deg(deg: float) -> np.ndarray:
    rad = math.radians(float(deg))
    mat = _mat_identity()
    c = math.cos(rad)
    s = math.sin(rad)
    mat[0, 0] = float(c)
    mat[0, 1] = float(-s)
    mat[1, 0] = float(s)
    mat[1, 1] = float(c)
    return mat

def _compose(*mats: np.ndarray) -> np.ndarray:
    out = _mat_identity()
    for mat in mats:
        out = (out @ mat).astype(np.float32)
    return out

def _sub_uv_rect(atlas: UVRect, face_idx: int, box: LocalBox) -> UVRect:
    u0_a, v0_a, u1_a, v1_a = atlas
    if int(face_idx) == FACE_POS_X:
        u0, u1 = float(box.mn_z), float(box.mx_z)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    elif int(face_idx) == FACE_NEG_X:
        u0, u1 = float(box.mx_z), float(box.mn_z)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    elif int(face_idx) == FACE_POS_Y:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_z), float(box.mx_z)
    elif int(face_idx) == FACE_NEG_Y:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mx_z), float(box.mn_z)
    elif int(face_idx) == FACE_POS_Z:
        u0, u1 = float(box.mx_x), float(box.mn_x)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    else:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_y), float(box.mx_y)

    return (float(u0_a + (u1_a - u0_a) * _clampf(u0, 0.0, 1.0)), float(v0_a + (v1_a - v0_a) * _clampf(v0, 0.0, 1.0)), float(u0_a + (u1_a - u0_a) * _clampf(u1, 0.0, 1.0)), float(v0_a + (v1_a - v0_a) * _clampf(v1, 0.0, 1.0)))

def _fence_gate_uv_rect(atlas: UVRect, face_idx: int, box: LocalBox) -> UVRect:
    u0_a, v0_a, u1_a, v1_a = atlas
    if int(face_idx) in (FACE_POS_X, FACE_NEG_X):
        u0, u1 = float(box.mn_z), float(box.mx_z)
        v0, v1 = float(box.mn_y), float(box.mx_y)
    elif int(face_idx) in (FACE_POS_Y, FACE_NEG_Y):
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_z), float(box.mx_z)
    else:
        u0, u1 = float(box.mn_x), float(box.mx_x)
        v0, v1 = float(box.mn_y), float(box.mx_y)

    return (float(u0_a + (u1_a - u0_a) * _clampf(u0, 0.0, 1.0)), float(v0_a + (v1_a - v0_a) * _clampf(v0, 0.0, 1.0)), float(u0_a + (u1_a - u0_a) * _clampf(u1, 0.0, 1.0)), float(v0_a + (v1_a - v0_a) * _clampf(v1, 0.0, 1.0)))

def _uv_rect_from_pixels(texture_uv: UVRect, px_rect: tuple[float, float, float, float]) -> UVRect:
    u0_a, v0_a, u1_a, v1_a = texture_uv
    px0, py0, px1, py1 = px_rect
    return (float(u0_a + (u1_a - u0_a) * (float(px0) / 16.0)), float(v0_a + (v1_a - v0_a) * (float(py0) / 16.0)), float(u0_a + (u1_a - u0_a) * (float(px1) / 16.0)), float(v0_a + (v1_a - v0_a) * (float(py1) / 16.0)))

def _skin_uv_rect(px_rect: tuple[float, float, float, float], width: int, height: int) -> UVRect:
    px0, py0, px1, py1 = px_rect
    w = max(1.0, float(width))
    h = max(1.0, float(height))
    return (float(px0) / w, 1.0 - float(py1) / h, float(px1) / w, 1.0 - float(py0) / h)

def _arm_swing_terms(first_person: FirstPersonRenderState) -> tuple[float, float, float, float]:
    swing = _clampf(float(first_person.swing_progress), 0.0, 1.0)
    root = math.sin(math.sqrt(swing) * math.pi)
    squared = math.sin(swing * swing * math.pi)
    full = math.sin(swing * math.pi)
    twice = math.sin(math.sqrt(swing) * math.pi * 2.0)
    return (float(root), float(squared), float(full), float(twice))

def build_main_hand_common_transform(first_person: FirstPersonRenderState) -> np.ndarray:
    equip_drop = 1.0 - _clampf(float(first_person.equip_progress), 0.0, 1.0)
    root, squared, full, twice = _arm_swing_terms(first_person)
    return _compose(_mat_translate(float(_ITEM_POS_X), float(_ITEM_POS_Y) + float(equip_drop) * -0.6, float(_ITEM_POS_Z)), _mat_rot_y_deg(float(_ITEM_PRESWING_ROT_Y_DEG)), _mat_translate(float(_ITEM_SWING_X_POS_SCALE) * float(root), float(_ITEM_SWING_Y_POS_SCALE) * float(twice), float(_ITEM_SWING_Z_POS_SCALE) * float(full)), _mat_rot_y_deg(float(_ITEM_SWING_Y_ROT_AMOUNT_DEG) * float(squared)), _mat_rot_z_deg(float(_ITEM_SWING_Z_ROT_AMOUNT_DEG) * float(root)), _mat_rot_x_deg(float(_ITEM_SWING_X_ROT_AMOUNT_DEG) * float(root)))

def build_first_person_item_camera_transform(first_person: FirstPersonRenderState) -> np.ndarray:
    return _compose(build_main_hand_common_transform(first_person), _mat_translate(float(_BLOCK_FIRSTPERSON_TRANSLATE_PX[0]) * _PX, float(_BLOCK_FIRSTPERSON_TRANSLATE_PX[1]) * _PX, float(_BLOCK_FIRSTPERSON_TRANSLATE_PX[2]) * _PX), _mat_rot_x_deg(float(_BLOCK_FIRSTPERSON_ROTATE_DEG[0])), _mat_rot_y_deg(float(_BLOCK_FIRSTPERSON_ROTATE_DEG[1])), _mat_rot_z_deg(float(_BLOCK_FIRSTPERSON_ROTATE_DEG[2])), _mat_scale(float(_BLOCK_FIRSTPERSON_SCALE[0]), float(_BLOCK_FIRSTPERSON_SCALE[1]), float(_BLOCK_FIRSTPERSON_SCALE[2])), _mat_translate(-0.5, -0.5, -0.5))

def build_third_person_item_hand_transform() -> np.ndarray:
    return _compose(_mat_translate(float(_BLOCK_THIRDPERSON_TRANSLATE_PX[0]) * _PX, float(_BLOCK_THIRDPERSON_TRANSLATE_PX[1]) * _PX, float(_BLOCK_THIRDPERSON_TRANSLATE_PX[2]) * _PX), _mat_rot_x_deg(float(_BLOCK_THIRDPERSON_ROTATE_DEG[0])), _mat_rot_y_deg(float(_BLOCK_THIRDPERSON_ROTATE_DEG[1])), _mat_rot_z_deg(float(_BLOCK_THIRDPERSON_ROTATE_DEG[2])), _mat_scale(float(_BLOCK_THIRDPERSON_SCALE[0]), float(_BLOCK_THIRDPERSON_SCALE[1]), float(_BLOCK_THIRDPERSON_SCALE[2])), _mat_translate(-0.5, -0.5, -0.5))

def build_first_person_arm_camera_transform(first_person: FirstPersonRenderState) -> np.ndarray:
    equip_drop = 1.0 - _clampf(float(first_person.equip_progress), 0.0, 1.0)
    root, squared, full, twice = _arm_swing_terms(first_person)
    return _compose(_mat_translate(float(_ARM_SWING_X_POS_SCALE) * float(root), float(_ARM_SWING_Y_POS_SCALE) * float(twice), float(_ARM_SWING_Z_POS_SCALE) * float(full)), _mat_translate(float(_ARM_POS_X), float(_ARM_POS_Y) + float(equip_drop) * -0.6, float(_ARM_POS_Z)), _mat_rot_y_deg(float(_ARM_PRESWING_ROT_Y_DEG)), _mat_rot_y_deg(float(_ARM_SWING_Y_ROT_AMOUNT_DEG) * float(root)), _mat_rot_z_deg(float(_ARM_SWING_Z_ROT_AMOUNT_DEG) * float(squared)), _mat_translate(float(_ARM_PREROTATION_X_OFFSET_PX) * _PX, float(_ARM_PREROTATION_Y_OFFSET_PX) * _PX, float(_ARM_PREROTATION_Z_OFFSET_PX) * _PX), _mat_rot_z_deg(float(_ARM_ROT_Z_DEG)), _mat_rot_x_deg(float(_ARM_ROT_X_DEG)), _mat_rot_y_deg(float(_ARM_ROT_Y_DEG)), _mat_translate(float(_ARM_POSTROTATION_X_OFFSET_PX) * _PX, 0.0, 0.0))

def held_block_model_boxes(block_id: str | None, def_lookup: DefLookup) -> tuple[TexturedBox, ...]:
    if block_id is None:
        return ()

    block_def = def_lookup(str(block_id))
    if block_def is None:
        return ()

    return held_block_model_boxes_for_kind(str(block_def.kind))

def held_block_model_boxes_for_kind(kind: str | None) -> tuple[TexturedBox, ...]:
    normalized = "" if kind is None else str(kind)
    if normalized == "slab":
        return tuple(TexturedBox(box=b) for b in boxes_for_slab({"type": "bottom"}))
    if normalized == "stairs":
        boxes = boxes_for_stairs(base_id="minecraft:stone_stairs", props={"facing": "east", "half": "bottom", "shape": "straight"}, get_state=(lambda _x, _y, _z: None), get_def=(lambda _block_id: None), x=0, y=0, z=0)
        return tuple(TexturedBox(box=b) for b in boxes)
    if normalized == "fence":
        return _FENCE_INVENTORY_BOXES
    if normalized == "fence_gate":
        return tuple(TexturedBox(box=b) for b in boxes_for_fence_gate({"facing": "south", "open": "false", "in_wall": "false"}))
    return (TexturedBox(box=LocalBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),)

def _empty_face_rows() -> tuple[np.ndarray, ...]:
    return tuple(np.zeros((0, 20), dtype=np.float32) for _ in range(6))

def _append_face_instance(buffers: list[list[list[float]]], face_idx: int, model: np.ndarray, uv_rect: UVRect) -> None:
    row = list(np.asarray(model, dtype=np.float32).reshape(16))
    row.extend([float(uv_rect[0]), float(uv_rect[1]), float(uv_rect[2]), float(uv_rect[3])])
    buffers[int(face_idx)].append(row)

def _face_uv_from_atlas(textured_box: TexturedBox, face_idx: int, texture_uv: UVRect, *, kind: str) -> UVRect:
    face_uv_pixels = textured_box.face_uv_pixels
    if face_uv_pixels is not None:
        px_rect = face_uv_pixels.get(int(face_idx))
        if px_rect is not None:
            return _uv_rect_from_pixels(texture_uv, px_rect)

    if kind == "fence_gate" and bool(textured_box.box.uv_hint):
        return _fence_gate_uv_rect(texture_uv, int(face_idx), textured_box.box)
    return _sub_uv_rect(texture_uv, int(face_idx), textured_box.box)

def _model_matrix_for_box(parent_transform: np.ndarray, box: LocalBox) -> np.ndarray:
    center_x = 0.5 * (float(box.mn_x) + float(box.mx_x))
    center_y = 0.5 * (float(box.mn_y) + float(box.mx_y))
    center_z = 0.5 * (float(box.mn_z) + float(box.mx_z))
    size_x = float(box.mx_x) - float(box.mn_x)
    size_y = float(box.mx_y) - float(box.mn_y)
    size_z = float(box.mx_z) - float(box.mn_z)
    return _compose(parent_transform, _mat_translate(center_x, center_y, center_z), _mat_scale(size_x, size_y, size_z))

def build_first_person_held_block_face_rows(first_person: FirstPersonRenderState | None, *, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, ...]:
    if first_person is None or first_person.visible_block_id is None:
        return _empty_face_rows()

    boxes = list(held_block_model_boxes(first_person.visible_block_id, def_lookup))
    if not boxes:
        return _empty_face_rows()

    block_def = def_lookup(str(first_person.visible_block_id))
    kind = "" if block_def is None else str(block_def.kind)
    parent_transform = build_first_person_item_camera_transform(first_person)

    buffers: list[list[list[float]]] = [[] for _ in range(6)]
    local_boxes = [tb.box for tb in boxes]
    for textured_box in boxes:
        for face_idx in range(6):
            if is_local_face_occluded(box=textured_box.box, face_idx=int(face_idx), boxes=local_boxes):
                continue
            texture_uv = uv_lookup(str(first_person.visible_block_id), int(face_idx))
            uv_rect = _face_uv_from_atlas(textured_box, int(face_idx), texture_uv, kind=kind)
            model = _model_matrix_for_box(parent_transform, textured_box.box)
            _append_face_instance(buffers, int(face_idx), model, uv_rect)

    return tuple(np.asarray(face_rows, dtype=np.float32) if face_rows else np.zeros((0, 20), dtype=np.float32) for face_rows in buffers)

def build_first_person_arm_face_rows(first_person: FirstPersonRenderState | None, *, skin_width: int, skin_height: int) -> tuple[np.ndarray, ...]:
    if first_person is None or (not bool(first_person.show_arm)):
        return _empty_face_rows()

    parent_transform = build_first_person_arm_camera_transform(first_person)
    buffers: list[list[list[float]]] = [[] for _ in range(6)]

    for box, uv_map in ((_ARM_BASE_BOX, _ALEX_RIGHT_ARM_BASE_UV_PX), (_ARM_SLEEVE_BOX, _ALEX_RIGHT_ARM_SLEEVE_UV_PX)):
        model = _model_matrix_for_box(parent_transform, box)
        for face_idx in range(6):
            uv_rect = _skin_uv_rect(uv_map[int(face_idx)], int(skin_width), int(skin_height))
            _append_face_instance(buffers, int(face_idx), model, uv_rect)

    return tuple(np.asarray(face_rows, dtype=np.float32) if face_rows else np.zeros((0, 20), dtype=np.float32) for face_rows in buffers)

def cube_rows_from_boxes(boxes: Sequence[LocalBox], parent_transform: np.ndarray) -> np.ndarray:
    if not boxes:
        return np.zeros((0, 16), dtype=np.float32)

    rows = []
    for box in boxes:
        rows.append(np.asarray(_model_matrix_for_box(parent_transform, box), dtype=np.float32).reshape(16))
    return np.ascontiguousarray(np.vstack(rows), dtype=np.float32)

def rotation_only(matrix: np.ndarray) -> np.ndarray:
    out = _mat_identity()
    linear = np.asarray(matrix, dtype=np.float32)[:3, :3].copy()
    for column in range(3):
        length = float(np.linalg.norm(linear[:, column]))
        if length > 1e-6:
            linear[:, column] /= length
    out[:3, :3] = linear
    return out

def rotation_scale_only(matrix: np.ndarray) -> np.ndarray:
    out = _mat_identity()
    out[:3, :3] = np.asarray(matrix, dtype=np.float32)[:3, :3]
    return out

def translate_matrix(x: float, y: float, z: float) -> np.ndarray:
    return _mat_translate(float(x), float(y), float(z))