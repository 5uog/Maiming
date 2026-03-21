# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Callable, Literal, Sequence
import math
import numpy as np

from ..math.scalars import clampf
from ..math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from ..blocks.block_definition import BlockDefinition
from ..blocks.models.common import LocalBox
from ..blocks.models.dimensions import px_box
from ..blocks.models.wall import boxes_for_wall
from ..blocks.models.fence_gate import boxes_for_fence_gate
from ..blocks.models.slab import boxes_for_slab
from ..blocks.models.stairs import boxes_for_stairs
from .face_occlusion import is_local_face_occluded
from ..math.transform_matrices import compose_matrices, identity_matrix, rotate_x_deg_matrix, rotate_y_deg_matrix, rotate_z_deg_matrix, scale_matrix, translate_matrix
from .uv_rects import UVRect, fence_gate_uv_rect, sub_uv_rect
from .player_render_state import FirstPersonRenderState

DefLookup = Callable[[str], BlockDefinition | None]
UVLookup = Callable[[str, int], UVRect]
TransformBuilder = Callable[[float], np.ndarray]
SafeFrame = tuple[float, float, float, float]
AnchorMode = Literal["nearest_zero", "min_edge", "max_edge"]

_PX = 1.0 / 16.0
FIRST_PERSON_HAND_NEAR = 0.05
_FIRST_PERSON_REFERENCE_FOV_DEG = 80.0
_FIRST_PERSON_REFERENCE_PROJECTION_Y = 1.0 / math.tan(math.radians(_FIRST_PERSON_REFERENCE_FOV_DEG) * 0.5)
FIRST_PERSON_ARM_HAND_ANCHOR = (0.0, -12.0 * _PX, 0.0)
THIRD_PERSON_RIGHT_HAND_ANCHOR = (0.0, -10.5 * _PX, 0.0)

_ITEM_POS_X = 1.22
_ITEM_POS_Y = -0.94
_ITEM_POS_Z = -1.05
_ITEM_SWING_X_POS_SCALE = -0.40
_ITEM_SWING_Y_POS_SCALE = 0.20
_ITEM_SWING_Z_POS_SCALE = -0.20
_ITEM_PRESWING_ROT_Y_DEG = 45.0
_ITEM_SWING_Y_ROT_AMOUNT_DEG = -20.0
_ITEM_SWING_Z_ROT_AMOUNT_DEG = -20.0
_ITEM_SWING_X_ROT_AMOUNT_DEG = -80.0

_ARM_POS_X = 1.44
_ARM_POS_Y = -0.84
_ARM_POS_Z = -1.0
_ARM_SWING_X_POS_SCALE = -0.30
_ARM_SWING_Y_POS_SCALE = 0.40
_ARM_SWING_Z_POS_SCALE = -0.40
_ARM_PRESWING_ROT_Y_DEG = 45.0
_ARM_SWING_Y_ROT_AMOUNT_DEG = -30.0
_ARM_SWING_Z_ROT_AMOUNT_DEG = 12.0
_ARM_PREROTATION_X_OFFSET_PX = -1.0
_ARM_PREROTATION_Y_OFFSET_PX = 3.6
_ARM_PREROTATION_Z_OFFSET_PX = 3.5
_ARM_ROT_Z_DEG = 60.0
_ARM_ROT_X_DEG = 140.0
_ARM_ROT_Y_DEG = -60.0
_ARM_POSTROTATION_X_OFFSET_PX = 5.6
_ARM_FIRSTPERSON_SCALE = 1.18

_BLOCK_FIRSTPERSON_TRANSLATE_PX = (0.0, 2.5, 0.0)
_BLOCK_FIRSTPERSON_ROTATE_DEG = (5.0, -45.0, 10.0)
_BLOCK_FIRSTPERSON_SCALE = (0.5, 0.5, 0.5)
_BLOCK_THIRDPERSON_TRANSLATE_PX = (0.0, 2.5, 0.0)
_BLOCK_THIRDPERSON_ROTATE_DEG = (75.0, 45.0, 0.0)
_BLOCK_THIRDPERSON_SCALE = (0.375, 0.375, 0.375)

_ARM_SAFE_FRAME: SafeFrame = (-0.98, 1.04, -1.74, 0.98)
_ITEM_SAFE_FRAME: SafeFrame = (-0.98, 1.01, -1.01, 0.98)
_ARM_PROJECTION_SCALE_EXPONENT = 0.55
_ITEM_PROJECTION_SCALE_EXPONENT = 0.45
_ARM_EQUIP_HIDE_DISTANCE = 1.18
_ITEM_EQUIP_HIDE_DISTANCE = 1.12
_RIGHT_EDGE_ANCHOR: AnchorMode = "max_edge"
_BOTTOM_EDGE_ANCHOR: AnchorMode = "min_edge"
_FIRST_PERSON_MIN_SCALE_MULTIPLIER = 0.25
_FIRST_PERSON_SCALE_SEARCH_STEPS = 18
_FIRST_PERSON_FIT_EPSILON = 1e-6

_ARM_BASE_BOX = LocalBox(-1.5 * _PX, -12.0 * _PX, -2.0 * _PX, 1.5 * _PX, 0.0, 2.0 * _PX)
_ARM_SLEEVE_BOX = LocalBox(-(1.5 + 0.25) * _PX, -(12.0 + 0.25) * _PX, -(2.0 + 0.25) * _PX,(1.5 + 0.25) * _PX, 0.25 * _PX,(2.0 + 0.25) * _PX)

@dataclass(frozen=True)
class TexturedBox:
    box: LocalBox
    face_uv_pixels: dict[int, tuple[float, float, float, float]] | None = None

_FENCE_INVENTORY_BOXES: tuple[TexturedBox, ...] = (TexturedBox(box=px_box(6, 0, 6, 10, 16, 10), face_uv_pixels={FACE_POS_X: (10.0, 0.0, 14.0, 16.0), FACE_NEG_X: (6.0, 0.0, 10.0, 16.0), FACE_POS_Y: (6.0, 6.0, 10.0, 10.0), FACE_NEG_Y: (10.0, 6.0, 14.0, 10.0), FACE_POS_Z: (6.0, 0.0, 10.0, 16.0), FACE_NEG_Z: (14.0, 0.0, 10.0, 16.0)}), TexturedBox(box=px_box(7, 6, -2, 9, 9, 18), face_uv_pixels={FACE_POS_X: (9.0, 6.0, 11.0, 9.0), FACE_NEG_X: (7.0, 6.0, 9.0, 9.0), FACE_POS_Y: (7.0, 0.0, 9.0, 4.0), FACE_NEG_Y: (9.0, 0.0, 11.0, 4.0), FACE_POS_Z: (7.0, 4.0, 9.0, 7.0), FACE_NEG_Z: (11.0, 4.0, 13.0, 7.0)}), TexturedBox(box=px_box(7, 12, -2, 9, 15, 18), face_uv_pixels={FACE_POS_X: (9.0, 12.0, 11.0, 15.0), FACE_NEG_X: (7.0, 12.0, 9.0, 15.0), FACE_POS_Y: (7.0, 7.0, 9.0, 11.0), FACE_NEG_Y: (9.0, 7.0, 11.0, 11.0), FACE_POS_Z: (7.0, 9.0, 9.0, 12.0), FACE_NEG_Z: (11.0, 9.0, 13.0, 12.0)}))
_WALL_INVENTORY_BOXES: tuple[TexturedBox, ...] = tuple(TexturedBox(box=b) for b in boxes_for_wall(props={"north": "low", "south": "low", "east": "none", "west": "none", "up": "true"}, get_state=(lambda _x, _y, _z: None), get_def=(lambda _block_id: None), x=0, y=0, z=0))
_HELD_BLOCK_KIND_SCALE_MULTIPLIERS: dict[str, float] = {"cube": 1.0, "slab": 1.0, "stairs": 1.0, "wall": 1.16, "fence": 1.12, "fence_gate": 1.72}

_ALEX_RIGHT_ARM_BASE_UV_PX = {FACE_POS_X: (40.0, 20.0, 44.0, 32.0), FACE_NEG_X: (47.0, 20.0, 51.0, 32.0), FACE_POS_Y: (44.0, 16.0, 47.0, 20.0), FACE_NEG_Y: (47.0, 16.0, 50.0, 20.0), FACE_POS_Z: (44.0, 20.0, 47.0, 32.0), FACE_NEG_Z: (51.0, 20.0, 54.0, 32.0)}
_ALEX_RIGHT_ARM_SLEEVE_UV_PX = {FACE_POS_X: (40.0, 36.0, 44.0, 48.0), FACE_NEG_X: (47.0, 36.0, 51.0, 48.0), FACE_POS_Y: (44.0, 32.0, 47.0, 36.0), FACE_NEG_Y: (47.0, 32.0, 50.0, 36.0), FACE_POS_Z: (44.0, 36.0, 47.0, 48.0), FACE_NEG_Z: (51.0, 36.0, 54.0, 48.0)}

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
    swing = clampf(float(first_person.swing_progress), 0.0, 1.0)
    root = math.sin(math.sqrt(swing) * math.pi)
    squared = math.sin(swing * swing * math.pi)
    full = math.sin(swing * math.pi)
    twice = math.sin(math.sqrt(swing) * math.pi * 2.0)
    return (float(root), float(squared), float(full), float(twice))

def _view_bob_transform(first_person: FirstPersonRenderState) -> np.ndarray:
    return compose_matrices(translate_matrix(float(first_person.view_bob_x), float(first_person.view_bob_y), float(first_person.view_bob_z)), rotate_z_deg_matrix(float(first_person.view_bob_roll_deg)), rotate_y_deg_matrix(float(first_person.view_bob_yaw_deg)), rotate_x_deg_matrix(float(first_person.view_bob_pitch_deg)))

def build_main_hand_common_transform(first_person: FirstPersonRenderState) -> np.ndarray:
    root, squared, full, twice = _arm_swing_terms(first_person)
    return compose_matrices(translate_matrix(float(_ITEM_SWING_X_POS_SCALE) * float(root), float(_ITEM_SWING_Y_POS_SCALE) * float(twice), float(_ITEM_SWING_Z_POS_SCALE) * float(full)), translate_matrix(float(_ITEM_POS_X), float(_ITEM_POS_Y), float(_ITEM_POS_Z)), rotate_y_deg_matrix(float(_ITEM_PRESWING_ROT_Y_DEG)), rotate_y_deg_matrix(float(_ITEM_SWING_Y_ROT_AMOUNT_DEG) * float(squared)), rotate_z_deg_matrix(float(_ITEM_SWING_Z_ROT_AMOUNT_DEG) * float(root)), rotate_x_deg_matrix(float(_ITEM_SWING_X_ROT_AMOUNT_DEG) * float(root)))

def build_first_person_item_camera_transform(first_person: FirstPersonRenderState, *, render_scale_multiplier: float=1.0) -> np.ndarray:
    uniform_scale = float(render_scale_multiplier)
    return compose_matrices(_view_bob_transform(first_person), build_main_hand_common_transform(first_person), translate_matrix(float(_BLOCK_FIRSTPERSON_TRANSLATE_PX[0]) * _PX, float(_BLOCK_FIRSTPERSON_TRANSLATE_PX[1]) * _PX, float(_BLOCK_FIRSTPERSON_TRANSLATE_PX[2]) * _PX), rotate_x_deg_matrix(float(_BLOCK_FIRSTPERSON_ROTATE_DEG[0])), rotate_y_deg_matrix(float(_BLOCK_FIRSTPERSON_ROTATE_DEG[1])), rotate_z_deg_matrix(float(_BLOCK_FIRSTPERSON_ROTATE_DEG[2])), scale_matrix(float(_BLOCK_FIRSTPERSON_SCALE[0]) * uniform_scale, float(_BLOCK_FIRSTPERSON_SCALE[1]) * uniform_scale, float(_BLOCK_FIRSTPERSON_SCALE[2]) * uniform_scale), translate_matrix(-0.5, -0.5, -0.5))

def build_third_person_item_hand_transform() -> np.ndarray:
    return compose_matrices(translate_matrix(float(_BLOCK_THIRDPERSON_TRANSLATE_PX[0]) * _PX, float(_BLOCK_THIRDPERSON_TRANSLATE_PX[1]) * _PX, float(_BLOCK_THIRDPERSON_TRANSLATE_PX[2]) * _PX), rotate_x_deg_matrix(float(_BLOCK_THIRDPERSON_ROTATE_DEG[0])), rotate_y_deg_matrix(float(_BLOCK_THIRDPERSON_ROTATE_DEG[1])), rotate_z_deg_matrix(float(_BLOCK_THIRDPERSON_ROTATE_DEG[2])), scale_matrix(float(_BLOCK_THIRDPERSON_SCALE[0]), float(_BLOCK_THIRDPERSON_SCALE[1]), float(_BLOCK_THIRDPERSON_SCALE[2])), translate_matrix(-0.5, -0.5, -0.5))

def build_first_person_arm_camera_transform(first_person: FirstPersonRenderState, *, render_scale_multiplier: float=1.0) -> np.ndarray:
    root, squared, full, twice = _arm_swing_terms(first_person)
    arm_scale = float(_ARM_FIRSTPERSON_SCALE) * float(render_scale_multiplier)
    return compose_matrices(_view_bob_transform(first_person), translate_matrix(float(_ARM_SWING_X_POS_SCALE) * float(root), float(_ARM_SWING_Y_POS_SCALE) * float(twice), float(_ARM_SWING_Z_POS_SCALE) * float(full)), translate_matrix(float(_ARM_POS_X), float(_ARM_POS_Y), float(_ARM_POS_Z)), rotate_y_deg_matrix(float(_ARM_PRESWING_ROT_Y_DEG)), rotate_y_deg_matrix(float(_ARM_SWING_Y_ROT_AMOUNT_DEG) * float(root)), rotate_z_deg_matrix(float(_ARM_SWING_Z_ROT_AMOUNT_DEG) * float(squared)), translate_matrix(float(_ARM_PREROTATION_X_OFFSET_PX) * _PX, float(_ARM_PREROTATION_Y_OFFSET_PX) * _PX, float(_ARM_PREROTATION_Z_OFFSET_PX) * _PX), rotate_z_deg_matrix(float(_ARM_ROT_Z_DEG)), rotate_x_deg_matrix(float(_ARM_ROT_X_DEG)), rotate_y_deg_matrix(float(_ARM_ROT_Y_DEG)), translate_matrix(float(_ARM_POSTROTATION_X_OFFSET_PX) * _PX, 0.0, 0.0), scale_matrix(arm_scale, arm_scale, arm_scale))

def held_block_model_boxes(block_id: str | None, def_lookup: DefLookup) -> tuple[TexturedBox, ...]:
    if block_id is None:
        return ()

    block_def = def_lookup(str(block_id))
    if block_def is None:
        return ()

    return held_block_model_boxes_for_kind(block_def.kind_name())

def held_block_model_boxes_for_kind(kind: str | None) -> tuple[TexturedBox, ...]:
    normalized = "" if kind is None else str(kind).strip().lower()
    if normalized == "slab":
        return tuple(TexturedBox(box=b) for b in boxes_for_slab({"type": "bottom"}))
    if normalized == "stairs":
        boxes = boxes_for_stairs(base_id="minecraft:stone_stairs", props={"facing": "east", "half": "bottom", "shape": "straight"}, get_state=(lambda _x, _y, _z: None), get_def=(lambda _block_id: None), x=0, y=0, z=0)
        return tuple(TexturedBox(box=b) for b in boxes)
    if normalized == "wall":
        return _WALL_INVENTORY_BOXES
    if normalized == "fence":
        return _FENCE_INVENTORY_BOXES
    if normalized == "fence_gate":
        return tuple(TexturedBox(box=b) for b in boxes_for_fence_gate({"facing": "south", "open": "false", "in_wall": "false"}))
    return (TexturedBox(box=LocalBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),)

def _held_block_kind_scale_multiplier(kind: str | None) -> float:
    normalized = "" if kind is None else str(kind).strip().lower()
    return float(_HELD_BLOCK_KIND_SCALE_MULTIPLIERS.get(normalized, 1.0))

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
        return fence_gate_uv_rect(texture_uv, int(face_idx), textured_box.box)
    return sub_uv_rect(texture_uv, int(face_idx), textured_box.box)

def _model_matrix_for_box(parent_transform: np.ndarray, box: LocalBox) -> np.ndarray:
    center_x = 0.5 * (float(box.mn_x) + float(box.mx_x))
    center_y = 0.5 * (float(box.mn_y) + float(box.mx_y))
    center_z = 0.5 * (float(box.mn_z) + float(box.mx_z))
    size_x = float(box.mx_x) - float(box.mn_x)
    size_y = float(box.mx_y) - float(box.mn_y)
    size_z = float(box.mx_z) - float(box.mn_z)
    return compose_matrices(parent_transform, translate_matrix(center_x, center_y, center_z), scale_matrix(size_x, size_y, size_z))

def _box_corner_rows(box: LocalBox) -> np.ndarray:
    return np.asarray([[float(x), float(y), float(z), 1.0] for x in (box.mn_x, box.mx_x) for y in (box.mn_y, box.mx_y) for z in (box.mn_z, box.mx_z)], dtype=np.float32)

def _camera_space_points(parent_transform: np.ndarray, boxes: Sequence[LocalBox]) -> np.ndarray:
    points = []
    transform = np.asarray(parent_transform, dtype=np.float32)
    for box in boxes:
        local_points = _box_corner_rows(box)
        points.append((transform @ local_points.T).T)
    if not points:
        return np.zeros((0, 4), dtype=np.float32)
    return np.ascontiguousarray(np.vstack(points), dtype=np.float32)

def _axis_translation_interval(points: np.ndarray, *, axis_index: int, projection_scale: float, ndc_min: float, ndc_max: float) -> tuple[float, float]:
    lower = -math.inf
    upper = math.inf
    proj = max(float(projection_scale), _FIRST_PERSON_FIT_EPSILON)
    for point in points:
        depth = max(-float(point[2]), _FIRST_PERSON_FIT_EPSILON)
        current_ndc = proj * float(point[axis_index]) / depth
        lower = max(lower,((float(ndc_min) - current_ndc) * depth) / proj)
        upper = min(upper,((float(ndc_max) - current_ndc) * depth) / proj)
    return (float(lower), float(upper))

def _fit_intervals(parent_transform: np.ndarray, boxes: Sequence[LocalBox], projection: np.ndarray, safe_frame: SafeFrame) -> tuple[tuple[float, float], tuple[float, float]]:
    projection_matrix = np.asarray(projection, dtype=np.float32)
    min_x, max_x, min_y, max_y = (float(safe_frame[0]), float(safe_frame[1]), float(safe_frame[2]), float(safe_frame[3]))
    points = _camera_space_points(parent_transform, boxes)
    x_interval = _axis_translation_interval(points, axis_index=0, projection_scale=float(projection_matrix[0, 0]), ndc_min=min_x, ndc_max=max_x)
    y_interval = _axis_translation_interval(points, axis_index=1, projection_scale=float(projection_matrix[1, 1]), ndc_min=min_y, ndc_max=max_y)
    return (x_interval, y_interval)

def _interval_is_feasible(interval: tuple[float, float]) -> bool:
    return float(interval[0]) <= float(interval[1])

def _projection_uniform_scale_multiplier(projection: np.ndarray, *, exponent: float) -> float:
    exp = float(exponent)
    if abs(exp) <= _FIRST_PERSON_FIT_EPSILON:
        return 1.0
    projection_matrix = np.asarray(projection, dtype=np.float32)
    current_projection_y = max(float(projection_matrix[1, 1]), _FIRST_PERSON_FIT_EPSILON)
    return float(pow(float(_FIRST_PERSON_REFERENCE_PROJECTION_Y) / current_projection_y, exp))

def _anchored_value_in_interval(value: float, interval: tuple[float, float], anchor_mode: AnchorMode) -> float:
    low, high = float(interval[0]), float(interval[1])
    if str(anchor_mode) == "min_edge":
        return low
    if str(anchor_mode) == "max_edge":
        return high
    if float(value) < low:
        return low
    if float(value) > high:
        return high
    return float(value)

def _clamp_value_to_interval(value: float, interval: tuple[float, float]) -> float:
    low, high = float(interval[0]), float(interval[1])
    if float(value) < low:
        return low
    if float(value) > high:
        return high
    return float(value)

def _neutral_swing_state(first_person: FirstPersonRenderState) -> FirstPersonRenderState:
    return replace(first_person, swing_progress=0.0, prev_swing_progress=0.0)

def _equip_hide_transform(first_person: FirstPersonRenderState, *, hide_distance: float) -> np.ndarray:
    hidden = 1.0 - clampf(float(first_person.equip_progress), 0.0, 1.0)
    eased = float(hidden * hidden * (3.0 - 2.0 * hidden))
    if eased <= _FIRST_PERSON_FIT_EPSILON:
        return identity_matrix()
    return translate_matrix(0.0, -float(hide_distance) * eased, 0.0)

def _fitted_first_person_parent_transform(*, boxes: Sequence[LocalBox], projection: np.ndarray, safe_frame: SafeFrame, transform_builder: TransformBuilder, projection_scale_exponent: float, x_anchor_mode: AnchorMode, y_anchor_mode: AnchorMode, reference_transform_builder: TransformBuilder | None=None) -> np.ndarray:
    projection_scale_multiplier = _projection_uniform_scale_multiplier(projection, exponent=float(projection_scale_exponent))
    best_scale = 1.0
    transform = np.asarray(transform_builder(projection_scale_multiplier), dtype=np.float32)
    x_interval, y_interval = _fit_intervals(transform, boxes, projection, safe_frame)
    if not (_interval_is_feasible(x_interval) and _interval_is_feasible(y_interval)):
        low = float(_FIRST_PERSON_MIN_SCALE_MULTIPLIER)
        best_scale = low
        low_transform = np.asarray(transform_builder(projection_scale_multiplier * low), dtype=np.float32)
        low_x_interval, low_y_interval = _fit_intervals(low_transform, boxes, projection, safe_frame)
        while low > _FIRST_PERSON_FIT_EPSILON and not (_interval_is_feasible(low_x_interval) and _interval_is_feasible(low_y_interval)):
            low *= 0.5
            best_scale = low
            low_transform = np.asarray(transform_builder(projection_scale_multiplier * low), dtype=np.float32)
            low_x_interval, low_y_interval = _fit_intervals(low_transform, boxes, projection, safe_frame)
        if _interval_is_feasible(low_x_interval) and _interval_is_feasible(low_y_interval):
            lo = low
            hi = 1.0
            best_scale = low
            for _ in range(_FIRST_PERSON_SCALE_SEARCH_STEPS):
                mid = 0.5 * (lo + hi)
                mid_transform = np.asarray(transform_builder(projection_scale_multiplier * mid), dtype=np.float32)
                mid_x_interval, mid_y_interval = _fit_intervals(mid_transform, boxes, projection, safe_frame)
                if _interval_is_feasible(mid_x_interval) and _interval_is_feasible(mid_y_interval):
                    best_scale = mid
                    lo = mid
                else:
                    hi = mid
        transform = np.asarray(transform_builder(projection_scale_multiplier * best_scale), dtype=np.float32)
        x_interval, y_interval = _fit_intervals(transform, boxes, projection, safe_frame)

    target_tx = 0.0
    target_ty = 0.0
    if reference_transform_builder is not None:
        reference_transform = np.asarray(reference_transform_builder(projection_scale_multiplier * best_scale), dtype=np.float32)
        reference_x_interval, reference_y_interval = _fit_intervals(reference_transform, boxes, projection, safe_frame)
        if _interval_is_feasible(reference_x_interval):
            target_tx = _anchored_value_in_interval(0.0, reference_x_interval, x_anchor_mode)
        if _interval_is_feasible(reference_y_interval):
            target_ty = _anchored_value_in_interval(0.0, reference_y_interval, y_anchor_mode)

    tx = _clamp_value_to_interval(target_tx, x_interval) if _interval_is_feasible(x_interval) else 0.0
    ty = _clamp_value_to_interval(target_ty, y_interval) if _interval_is_feasible(y_interval) else 0.0
    return compose_matrices(translate_matrix(float(tx), float(ty), 0.0), transform)

def build_first_person_held_block_face_rows(first_person: FirstPersonRenderState | None, *, projection: np.ndarray, uv_lookup: UVLookup, def_lookup: DefLookup) -> tuple[np.ndarray, ...]:
    if first_person is None or first_person.visible_block_id is None:
        return _empty_face_rows()

    boxes = list(held_block_model_boxes(first_person.visible_block_id, def_lookup))
    if not boxes:
        return _empty_face_rows()

    block_def = def_lookup(str(first_person.visible_block_id))
    kind = "" if block_def is None else str(block_def.kind_name())
    kind_scale = _held_block_kind_scale_multiplier(kind)
    base_parent_transform = _fitted_first_person_parent_transform(boxes=[textured_box.box for textured_box in boxes], projection=projection, safe_frame=_ITEM_SAFE_FRAME, transform_builder=(lambda scale_multiplier: build_first_person_item_camera_transform(first_person, render_scale_multiplier=float(scale_multiplier) * float(kind_scale))), projection_scale_exponent=float(_ITEM_PROJECTION_SCALE_EXPONENT), x_anchor_mode=_RIGHT_EDGE_ANCHOR, y_anchor_mode=_BOTTOM_EDGE_ANCHOR, reference_transform_builder=(lambda scale_multiplier: build_first_person_item_camera_transform(_neutral_swing_state(first_person), render_scale_multiplier=float(scale_multiplier) * float(kind_scale))))
    parent_transform = compose_matrices(_equip_hide_transform(first_person, hide_distance=float(_ITEM_EQUIP_HIDE_DISTANCE)), base_parent_transform)

    buffers: list[list[list[float]]] = [[] for _ in range(6)]
    local_boxes = [textured_box.box for textured_box in boxes]
    for textured_box in boxes:
        for face_idx in range(6):
            if is_local_face_occluded(box=textured_box.box, face_idx=int(face_idx), boxes=local_boxes):
                continue
            texture_uv = uv_lookup(str(first_person.visible_block_id), int(face_idx))
            uv_rect = _face_uv_from_atlas(textured_box, int(face_idx), texture_uv, kind=kind)
            model = _model_matrix_for_box(parent_transform, textured_box.box)
            _append_face_instance(buffers, int(face_idx), model, uv_rect)

    return tuple(np.asarray(face_rows, dtype=np.float32) if face_rows else np.zeros((0, 20), dtype=np.float32) for face_rows in buffers)

def build_first_person_arm_face_rows(first_person: FirstPersonRenderState | None, *, projection: np.ndarray, skin_width: int, skin_height: int) -> tuple[np.ndarray, ...]:
    if first_person is None or (not bool(first_person.show_arm)):
        return _empty_face_rows()

    arm_boxes = (_ARM_BASE_BOX, _ARM_SLEEVE_BOX)
    base_parent_transform = _fitted_first_person_parent_transform(boxes=arm_boxes, projection=projection, safe_frame=_ARM_SAFE_FRAME, transform_builder=(lambda scale_multiplier: build_first_person_arm_camera_transform(first_person, render_scale_multiplier=float(scale_multiplier))), projection_scale_exponent=float(_ARM_PROJECTION_SCALE_EXPONENT), x_anchor_mode=_RIGHT_EDGE_ANCHOR, y_anchor_mode=_BOTTOM_EDGE_ANCHOR, reference_transform_builder=(lambda scale_multiplier: build_first_person_arm_camera_transform(_neutral_swing_state(first_person), render_scale_multiplier=float(scale_multiplier))))
    parent_transform = compose_matrices(_equip_hide_transform(first_person, hide_distance=float(_ARM_EQUIP_HIDE_DISTANCE)), base_parent_transform)
    buffers: list[list[list[float]]] = [[] for _ in range(6)]

    for box, uv_map in ((arm_boxes[0], _ALEX_RIGHT_ARM_BASE_UV_PX),(arm_boxes[1], _ALEX_RIGHT_ARM_SLEEVE_UV_PX)):
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
    out = identity_matrix()
    linear = np.asarray(matrix, dtype=np.float32)[:3, :3].copy()
    for column in range(3):
        length = float(np.linalg.norm(linear[:, column]))
        if length > 1e-6:
            linear[:, column] /= length
    out[:3, :3] = linear
    return out

def rotation_scale_only(matrix: np.ndarray) -> np.ndarray:
    out = identity_matrix()
    out[:3, :3] = np.asarray(matrix, dtype=np.float32)[:3, :3]
    return out