# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

from ..blocks.models.common import LocalBox
from ..math.scalars import clampf
from ..math.transform_matrices import compose_matrices, rotate_x_rad_matrix, rotate_y_rad_matrix, rotate_z_rad_matrix, scale_matrix, translate_matrix
from ..math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from .first_person_geometry import THIRD_PERSON_RIGHT_HAND_ANCHOR, build_third_person_item_hand_transform, cube_rows_from_boxes, held_block_model_boxes_for_kind
from .player_render_state import PlayerRenderState

_PX = 1.0 / 16.0
_SKIN_WIDTH = 64.0
_SKIN_HEIGHT = 64.0

_HEAD_SIZE = (8.0 * _PX, 8.0 * _PX, 8.0 * _PX)
_HEAD_OUTER_SIZE = (9.0 * _PX, 9.0 * _PX, 9.0 * _PX)
_BODY_SIZE = (8.0 * _PX, 12.0 * _PX, 4.0 * _PX)
_BODY_OUTER_SIZE = (8.5 * _PX, 12.5 * _PX, 4.5 * _PX)
_ARM_SIZE_SLIM = (3.0 * _PX, 12.0 * _PX, 4.0 * _PX)
_ARM_OUTER_SIZE_SLIM = (3.5 * _PX, 12.5 * _PX, 4.5 * _PX)
_LEG_SIZE = (4.0 * _PX, 12.0 * _PX, 4.0 * _PX)
_LEG_OUTER_SIZE = (4.5 * _PX, 12.5 * _PX, 4.5 * _PX)

_MODEL_FEET_OFFSET_Y = 24.0 * _PX
_HEAD_GROUP_POS = (0.0, 0.0, 0.0)
_HEAD_CENTER = (0.0, 4.0 * _PX, 0.0)
_BODY_GROUP_POS_STAND = (0.0, -6.0 * _PX, 0.0)
_RIGHT_ARM_GROUP_POS_STAND = (-5.0 * _PX, -2.0 * _PX, 0.0)
_LEFT_ARM_GROUP_POS_STAND = (5.0 * _PX, -2.0 * _PX, 0.0)
_RIGHT_ARM_PIVOT_SLIM = (-0.5 * _PX, -4.5 * _PX, 0.0)
_LEFT_ARM_PIVOT_SLIM = (0.5 * _PX, -4.5 * _PX, 0.0)
_RIGHT_LEG_GROUP_POS_STAND = (-2.0 * _PX, -12.0 * _PX, 0.0)
_LEFT_LEG_GROUP_POS_STAND = (2.0 * _PX, -12.0 * _PX, 0.0)
_LEG_PIVOT = (0.0, -6.0 * _PX, 0.0)

_CROUCH_BODY_ROT_X = 0.4537860552
_CROUCH_BODY_POS_Y = -8.103677462 * _PX
_CROUCH_BODY_POS_Z = (1.3256181 - 3.4500310377) * _PX
_CROUCH_HEAD_POS_Y = -3.618325234674 * _PX
_CROUCH_ARM_POS_Y = -4.53943318 * _PX
_CROUCH_ARM_POS_Z = (3.618325234674 - 3.4500310377) * _PX
_CROUCH_ARM_ROT_X = 0.410367746202
_CROUCH_ARM_ROT_Z = 0.1
_CROUCH_LEG_POS_Z = -3.4500310377 * _PX
_ARM_SWAY_Z = math.pi * 0.02

_WORLD_SPECIAL_ITEM_BOX = LocalBox(1.0 * _PX, 1.0 * _PX, 7.5 * _PX, 15.0 * _PX, 15.0 * _PX, 8.5 * _PX)
_WORLD_SPECIAL_ITEM_SCALE = 1.75

def _skin_cube_uv_map(*, pos_x: tuple[float, float, float, float], neg_x: tuple[float, float, float, float], pos_y: tuple[float, float, float, float], neg_y: tuple[float, float, float, float], pos_z: tuple[float, float, float, float], neg_z: tuple[float, float, float, float]) -> dict[int, tuple[float, float, float, float]]:
    return {FACE_POS_X: pos_x, FACE_NEG_X: neg_x, FACE_POS_Y: pos_y, FACE_NEG_Y: neg_y, FACE_POS_Z: pos_z, FACE_NEG_Z: neg_z}

def _rotate_uv_rect_180(px_rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return (float(px_rect[2]), float(px_rect[3]), float(px_rect[0]), float(px_rect[1]))

def _uv_map_with_rotated_faces(uv_map: dict[int, tuple[float, float, float, float]], *faces: int) -> dict[int, tuple[float, float, float, float]]:
    out = {int(face_idx): tuple(rect) for face_idx, rect in uv_map.items()}
    for face_idx in faces:
        out[int(face_idx)] = _rotate_uv_rect_180(out[int(face_idx)])
    return out

_HEAD_BASE_UV_PX = _skin_cube_uv_map(pos_x=(0.0, 8.0, 8.0, 16.0), neg_x=(16.0, 8.0, 24.0, 16.0), pos_y=(8.0, 0.0, 16.0, 8.0), neg_y=(16.0, 0.0, 24.0, 8.0), pos_z=(8.0, 8.0, 16.0, 16.0), neg_z=(24.0, 8.0, 32.0, 16.0))
_HEAD_HAT_UV_PX = _skin_cube_uv_map(pos_x=(32.0, 8.0, 40.0, 16.0), neg_x=(48.0, 8.0, 56.0, 16.0), pos_y=(40.0, 0.0, 48.0, 8.0), neg_y=(48.0, 0.0, 56.0, 8.0), pos_z=(40.0, 8.0, 48.0, 16.0), neg_z=(56.0, 8.0, 64.0, 16.0))
_BODY_BASE_UV_PX = _uv_map_with_rotated_faces(_skin_cube_uv_map(pos_x=(16.0, 20.0, 20.0, 32.0), neg_x=(28.0, 20.0, 32.0, 32.0), pos_y=(20.0, 16.0, 28.0, 20.0), neg_y=(28.0, 16.0, 36.0, 20.0), pos_z=(20.0, 20.0, 28.0, 32.0), neg_z=(32.0, 20.0, 40.0, 32.0)), FACE_POS_Y)
_BODY_JACKET_UV_PX = _uv_map_with_rotated_faces(_skin_cube_uv_map(pos_x=(16.0, 36.0, 20.0, 48.0), neg_x=(28.0, 36.0, 32.0, 48.0), pos_y=(20.0, 32.0, 28.0, 36.0), neg_y=(28.0, 32.0, 36.0, 36.0), pos_z=(20.0, 36.0, 28.0, 48.0), neg_z=(32.0, 36.0, 40.0, 48.0)), FACE_POS_Y)
_RIGHT_ARM_BASE_UV_PX = _skin_cube_uv_map(pos_x=(40.0, 20.0, 44.0, 32.0), neg_x=(47.0, 20.0, 51.0, 32.0), pos_y=(44.0, 16.0, 47.0, 20.0), neg_y=(47.0, 16.0, 50.0, 20.0), pos_z=(44.0, 20.0, 47.0, 32.0), neg_z=(51.0, 20.0, 54.0, 32.0))
_RIGHT_ARM_SLEEVE_UV_PX = _skin_cube_uv_map(pos_x=(40.0, 36.0, 44.0, 48.0), neg_x=(47.0, 36.0, 51.0, 48.0), pos_y=(44.0, 32.0, 47.0, 36.0), neg_y=(47.0, 32.0, 50.0, 36.0), pos_z=(44.0, 36.0, 47.0, 48.0), neg_z=(51.0, 36.0, 54.0, 48.0))
_LEFT_ARM_BASE_UV_PX = _skin_cube_uv_map(pos_x=(32.0, 52.0, 36.0, 64.0), neg_x=(39.0, 52.0, 43.0, 64.0), pos_y=(36.0, 48.0, 39.0, 52.0), neg_y=(39.0, 48.0, 42.0, 52.0), pos_z=(36.0, 52.0, 39.0, 64.0), neg_z=(43.0, 52.0, 46.0, 64.0))
_LEFT_ARM_SLEEVE_UV_PX = _skin_cube_uv_map(pos_x=(48.0, 52.0, 52.0, 64.0), neg_x=(55.0, 52.0, 59.0, 64.0), pos_y=(52.0, 48.0, 55.0, 52.0), neg_y=(55.0, 48.0, 58.0, 52.0), pos_z=(52.0, 52.0, 55.0, 64.0), neg_z=(59.0, 52.0, 62.0, 64.0))
_VISUAL_RIGHT_ARM_BASE_UV_PX = _uv_map_with_rotated_faces(_RIGHT_ARM_BASE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
_VISUAL_RIGHT_ARM_SLEEVE_UV_PX = _uv_map_with_rotated_faces(_RIGHT_ARM_SLEEVE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
_VISUAL_LEFT_ARM_BASE_UV_PX = _uv_map_with_rotated_faces(_LEFT_ARM_BASE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
_VISUAL_LEFT_ARM_SLEEVE_UV_PX = _uv_map_with_rotated_faces(_LEFT_ARM_SLEEVE_UV_PX, FACE_POS_Y, FACE_NEG_Y)
_RIGHT_LEG_BASE_UV_PX = _skin_cube_uv_map(pos_x=(0.0, 20.0, 4.0, 32.0), neg_x=(8.0, 20.0, 12.0, 32.0), pos_y=(4.0, 16.0, 8.0, 20.0), neg_y=(8.0, 16.0, 12.0, 20.0), pos_z=(4.0, 20.0, 8.0, 32.0), neg_z=(12.0, 20.0, 16.0, 32.0))
_RIGHT_LEG_PANTS_UV_PX = _skin_cube_uv_map(pos_x=(0.0, 36.0, 4.0, 48.0), neg_x=(8.0, 36.0, 12.0, 48.0), pos_y=(4.0, 32.0, 8.0, 36.0), neg_y=(8.0, 32.0, 12.0, 36.0), pos_z=(4.0, 36.0, 8.0, 48.0), neg_z=(12.0, 36.0, 16.0, 48.0))
_LEFT_LEG_BASE_UV_PX = _skin_cube_uv_map(pos_x=(16.0, 52.0, 20.0, 64.0), neg_x=(24.0, 52.0, 28.0, 64.0), pos_y=(20.0, 48.0, 24.0, 52.0), neg_y=(24.0, 48.0, 28.0, 52.0), pos_z=(20.0, 52.0, 24.0, 64.0), neg_z=(28.0, 52.0, 32.0, 64.0))
_LEFT_LEG_PANTS_UV_PX = _skin_cube_uv_map(pos_x=(0.0, 52.0, 4.0, 64.0), neg_x=(8.0, 52.0, 12.0, 64.0), pos_y=(4.0, 48.0, 8.0, 52.0), neg_y=(8.0, 48.0, 12.0, 52.0), pos_z=(4.0, 52.0, 8.0, 64.0), neg_z=(12.0, 52.0, 16.0, 64.0))

@dataclass(frozen=True)
class HeldBlockPose:
    block_id: str
    block_kind: str | None
    parent_transform: np.ndarray

@dataclass(frozen=True)
class PlayerModelPose:
    skin_face_rows: tuple[np.ndarray, ...]
    held_block_pose: HeldBlockPose | None
    special_item_face_rows: tuple[np.ndarray, ...]
    visible_special_item_icon: str | None
    shadow_rows: np.ndarray

def _lerp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)

def _as_rows(matrix: np.ndarray) -> np.ndarray:
    return np.asarray(matrix, dtype=np.float32).reshape(16)

def _empty_face_rows() -> tuple[np.ndarray, ...]:
    return tuple(np.zeros((0, 20), dtype=np.float32) for _ in range(6))

def _skin_uv_rect(px_rect: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    px0, py0, px1, py1 = px_rect
    return (float(px0) / float(_SKIN_WIDTH), 1.0 - float(py1) / float(_SKIN_HEIGHT), float(px1) / float(_SKIN_WIDTH), 1.0 - float(py0) / float(_SKIN_HEIGHT))

def _append_face_instance(buffers: list[list[list[float]]], face_idx: int, model: np.ndarray, uv_rect: tuple[float, float, float, float]) -> None:
    row = list(np.asarray(model, dtype=np.float32).reshape(16))
    row.extend([float(uv_rect[0]), float(uv_rect[1]), float(uv_rect[2]), float(uv_rect[3])])
    buffers[int(face_idx)].append(row)

def _rows_from_buffers(buffers: list[list[list[float]]]) -> tuple[np.ndarray, ...]:
    return tuple(np.asarray(face_rows, dtype=np.float32) if face_rows else np.zeros((0, 20), dtype=np.float32) for face_rows in buffers)

def _append_unit_cube_rows(buffers: list[list[list[float]]], model: np.ndarray, uv_map_pixels: dict[int, tuple[float, float, float, float]]) -> None:
    for face_idx in range(6):
        _append_face_instance(buffers, int(face_idx), model, _skin_uv_rect(uv_map_pixels[int(face_idx)]))

def _model_matrix_for_box(parent_transform: np.ndarray, box: LocalBox) -> np.ndarray:
    center_x = 0.5 * (float(box.mn_x) + float(box.mx_x))
    center_y = 0.5 * (float(box.mn_y) + float(box.mx_y))
    center_z = 0.5 * (float(box.mn_z) + float(box.mx_z))
    size_x = float(box.mx_x) - float(box.mn_x)
    size_y = float(box.mx_y) - float(box.mn_y)
    size_z = float(box.mx_z) - float(box.mn_z)
    return compose_matrices(parent_transform, translate_matrix(center_x, center_y, center_z), scale_matrix(size_x, size_y, size_z))

def _shadow_attack_angles(swing_progress: float) -> tuple[float, float, float]:
    swing = clampf(float(swing_progress), 0.0, 1.0)
    if swing <= 1e-6:
        return (0.0, 0.0, 0.0)

    root = math.sin(math.sqrt(swing) * math.pi)
    full = math.sin(swing * math.pi)
    eased = 1.0 - pow(1.0 - swing, 4.0)
    attack_x = -1.2 * math.sin(eased * math.pi)
    attack_y = -0.35 * root
    attack_z = -0.4 * full
    return (float(attack_x), float(attack_y), float(attack_z))

def _attack_swing_weight(swing_progress: float) -> float:
    swing = clampf(float(swing_progress), 0.0, 1.0)
    if swing <= 1e-6:
        return 0.0
    return float(math.sin(math.sqrt(swing) * math.pi))

def build_player_model_pose(state: PlayerRenderState | None) -> PlayerModelPose:
    empty_shadow = np.zeros((0, 16), dtype=np.float32)
    empty_faces = _empty_face_rows()
    if state is None:
        return PlayerModelPose(skin_face_rows=empty_faces, held_block_pose=None, special_item_face_rows=empty_faces, visible_special_item_icon=None, shadow_rows=empty_shadow)

    crouch = clampf(float(state.crouch_amount), 0.0, 1.0)
    body_yaw = math.radians(float(state.body_yaw_deg))
    head_yaw = math.radians(float(state.head_yaw_deg))
    head_pitch = math.radians(float(state.head_pitch_deg))
    phase = float(state.limb_phase_rad)
    swing = max(0.0, float(state.limb_swing_amount))
    walk_l = math.sin(float(phase))
    walk_r = math.sin(float(phase) + math.pi)
    arm_sway = float(clampf(float(swing) / 0.5 if float(swing) > 1e-9 else 0.0, 0.0, 1.0)) * float(_ARM_SWAY_Z)
    right_arm_rot_x = float(swing) * float(walk_l) + float(_CROUCH_ARM_ROT_X) * float(crouch)
    right_arm_rot_z = -(float(arm_sway) + float(_CROUCH_ARM_ROT_Z) * float(crouch))
    right_leg_rot_x = float(swing) * float(walk_r)
    left_leg_rot_x = float(swing) * float(walk_l)

    attack_x = 0.0
    attack_y = 0.0
    attack_z = 0.0
    attack_weight = 0.0
    first_person = state.first_person
    if first_person is not None:
        attack_x, attack_y, attack_z = _shadow_attack_angles(float(first_person.swing_progress))
        attack_weight = _attack_swing_weight(float(first_person.swing_progress))

    main_hand_walk_damping = 1.0 - 0.85 * float(attack_weight)
    main_hand_sway_damping = 1.0 - 0.70 * float(attack_weight)
    left_arm_rot_x = (float(swing) * float(walk_r) * float(main_hand_walk_damping)) + float(_CROUCH_ARM_ROT_X) * float(crouch) + float(attack_x)
    left_arm_rot_z = (float(arm_sway) * float(main_hand_sway_damping)) + float(_CROUCH_ARM_ROT_Z) * float(crouch) + float(attack_z)
    if float(attack_weight) > 1e-6:
        left_arm_rot_x = min(float(left_arm_rot_x), 0.08 * (1.0 - float(attack_weight)))

    root = compose_matrices(translate_matrix(float(state.base_x), float(state.base_y), float(state.base_z)), rotate_y_rad_matrix(float(body_yaw)), translate_matrix(0.0, float(_MODEL_FEET_OFFSET_Y), 0.0))
    head_group_y = _lerp(float(_HEAD_GROUP_POS[1]), float(_CROUCH_HEAD_POS_Y), float(crouch))
    body_group_y = _lerp(float(_BODY_GROUP_POS_STAND[1]), float(_CROUCH_BODY_POS_Y), float(crouch))
    body_group_z = _lerp(0.0, float(_CROUCH_BODY_POS_Z), float(crouch))
    arm_group_y = _lerp(float(_RIGHT_ARM_GROUP_POS_STAND[1]), float(_CROUCH_ARM_POS_Y), float(crouch))
    arm_group_z = _lerp(0.0, float(_CROUCH_ARM_POS_Z), float(crouch))
    leg_group_z = _lerp(0.0, float(_CROUCH_LEG_POS_Z), float(crouch))

    head_parent = compose_matrices(root, translate_matrix(0.0, float(head_group_y), 0.0), rotate_y_rad_matrix(float(head_yaw)), rotate_x_rad_matrix(float(head_pitch)), translate_matrix(float(_HEAD_CENTER[0]), float(_HEAD_CENTER[1]), float(_HEAD_CENTER[2])))
    body_parent = compose_matrices(root, translate_matrix(0.0, float(body_group_y), float(body_group_z)), rotate_x_rad_matrix(float(_CROUCH_BODY_ROT_X) * float(crouch)))
    right_arm_parent = compose_matrices(root, translate_matrix(float(_RIGHT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), rotate_z_rad_matrix(float(right_arm_rot_z)), rotate_x_rad_matrix(float(right_arm_rot_x)))
    left_arm_parent = compose_matrices(root, translate_matrix(float(_LEFT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), rotate_z_rad_matrix(float(left_arm_rot_z)), rotate_y_rad_matrix(float(attack_y)), rotate_x_rad_matrix(float(left_arm_rot_x)))
    right_leg_parent = compose_matrices(root, translate_matrix(float(_RIGHT_LEG_GROUP_POS_STAND[0]), float(_RIGHT_LEG_GROUP_POS_STAND[1]), float(leg_group_z)), rotate_x_rad_matrix(float(right_leg_rot_x)), translate_matrix(float(_LEG_PIVOT[0]), float(_LEG_PIVOT[1]), float(_LEG_PIVOT[2])))
    left_leg_parent = compose_matrices(root, translate_matrix(float(_LEFT_LEG_GROUP_POS_STAND[0]), float(_LEFT_LEG_GROUP_POS_STAND[1]), float(leg_group_z)), rotate_x_rad_matrix(float(left_leg_rot_x)), translate_matrix(float(_LEG_PIVOT[0]), float(_LEG_PIVOT[1]), float(_LEG_PIVOT[2])))

    head = compose_matrices(head_parent, scale_matrix(float(_HEAD_SIZE[0]), float(_HEAD_SIZE[1]), float(_HEAD_SIZE[2])))
    hat = compose_matrices(head_parent, scale_matrix(float(_HEAD_OUTER_SIZE[0]), float(_HEAD_OUTER_SIZE[1]), float(_HEAD_OUTER_SIZE[2])))
    body = compose_matrices(body_parent, scale_matrix(float(_BODY_SIZE[0]), float(_BODY_SIZE[1]), float(_BODY_SIZE[2])))
    jacket = compose_matrices(body_parent, scale_matrix(float(_BODY_OUTER_SIZE[0]), float(_BODY_OUTER_SIZE[1]), float(_BODY_OUTER_SIZE[2])))
    right_arm = compose_matrices(right_arm_parent, translate_matrix(float(_RIGHT_ARM_PIVOT_SLIM[0]), float(_RIGHT_ARM_PIVOT_SLIM[1]), float(_RIGHT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))
    right_sleeve = compose_matrices(right_arm_parent, translate_matrix(float(_RIGHT_ARM_PIVOT_SLIM[0]), float(_RIGHT_ARM_PIVOT_SLIM[1]), float(_RIGHT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_OUTER_SIZE_SLIM[0]), float(_ARM_OUTER_SIZE_SLIM[1]), float(_ARM_OUTER_SIZE_SLIM[2])))
    left_arm = compose_matrices(left_arm_parent, translate_matrix(float(_LEFT_ARM_PIVOT_SLIM[0]), float(_LEFT_ARM_PIVOT_SLIM[1]), float(_LEFT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))
    left_sleeve = compose_matrices(left_arm_parent, translate_matrix(float(_LEFT_ARM_PIVOT_SLIM[0]), float(_LEFT_ARM_PIVOT_SLIM[1]), float(_LEFT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_OUTER_SIZE_SLIM[0]), float(_ARM_OUTER_SIZE_SLIM[1]), float(_ARM_OUTER_SIZE_SLIM[2])))
    right_leg = compose_matrices(right_leg_parent, scale_matrix(float(_LEG_SIZE[0]), float(_LEG_SIZE[1]), float(_LEG_SIZE[2])))
    right_pants = compose_matrices(right_leg_parent, scale_matrix(float(_LEG_OUTER_SIZE[0]), float(_LEG_OUTER_SIZE[1]), float(_LEG_OUTER_SIZE[2])))
    left_leg = compose_matrices(left_leg_parent, scale_matrix(float(_LEG_SIZE[0]), float(_LEG_SIZE[1]), float(_LEG_SIZE[2])))
    left_pants = compose_matrices(left_leg_parent, scale_matrix(float(_LEG_OUTER_SIZE[0]), float(_LEG_OUTER_SIZE[1]), float(_LEG_OUTER_SIZE[2])))

    shadow_rows_list = [_as_rows(head), _as_rows(body), _as_rows(right_arm), _as_rows(left_arm), _as_rows(right_leg), _as_rows(left_leg)]

    held_block_pose: HeldBlockPose | None = None
    special_item_face_rows = empty_faces
    visible_special_item_icon: str | None = None
    if first_person is not None:
        hand_anchor = compose_matrices(left_arm_parent, translate_matrix(float(THIRD_PERSON_RIGHT_HAND_ANCHOR[0]), float(THIRD_PERSON_RIGHT_HAND_ANCHOR[1]), float(THIRD_PERSON_RIGHT_HAND_ANCHOR[2])))
        if first_person.visible_block_id is not None and first_person.visible_block_kind is not None:
            held_parent = compose_matrices(hand_anchor, build_third_person_item_hand_transform())
            block_boxes = [textured_box.box for textured_box in held_block_model_boxes_for_kind(first_person.visible_block_kind)]
            block_shadow_rows = cube_rows_from_boxes(block_boxes, held_parent)
            if block_shadow_rows.size > 0:
                shadow_rows_list.extend([row for row in block_shadow_rows])
            if not bool(state.is_first_person):
                held_block_pose = HeldBlockPose(block_id=str(first_person.visible_block_id), block_kind=str(first_person.visible_block_kind), parent_transform=np.asarray(held_parent, dtype=np.float32))
        elif first_person.visible_special_item_icon is not None:
            special_parent = compose_matrices(hand_anchor, build_third_person_item_hand_transform(), scale_matrix(float(_WORLD_SPECIAL_ITEM_SCALE), float(_WORLD_SPECIAL_ITEM_SCALE), 1.0))
            special_shadow_rows = cube_rows_from_boxes((_WORLD_SPECIAL_ITEM_BOX,), special_parent)
            if special_shadow_rows.size > 0:
                shadow_rows_list.extend([row for row in special_shadow_rows])
            if not bool(state.is_first_person):
                buffers: list[list[list[float]]] = [[] for _ in range(6)]
                special_model = _model_matrix_for_box(special_parent, _WORLD_SPECIAL_ITEM_BOX)
                _append_face_instance(buffers, int(FACE_POS_Z), special_model, (0.0, 0.0, 1.0, 1.0))
                special_item_face_rows = _rows_from_buffers(buffers)
                visible_special_item_icon = str(first_person.visible_special_item_icon)

    shadow_rows = np.ascontiguousarray(np.vstack(shadow_rows_list), dtype=np.float32)

    if bool(state.is_first_person):
        return PlayerModelPose(skin_face_rows=empty_faces, held_block_pose=None, special_item_face_rows=empty_faces, visible_special_item_icon=None, shadow_rows=shadow_rows)

    skin_buffers: list[list[list[float]]] = [[] for _ in range(6)]
    for model, uv_map in ((head, _HEAD_BASE_UV_PX),(hat, _HEAD_HAT_UV_PX),(body, _BODY_BASE_UV_PX),(jacket, _BODY_JACKET_UV_PX),(right_arm, _VISUAL_LEFT_ARM_BASE_UV_PX),(right_sleeve, _VISUAL_LEFT_ARM_SLEEVE_UV_PX),(left_arm, _VISUAL_RIGHT_ARM_BASE_UV_PX),(left_sleeve, _VISUAL_RIGHT_ARM_SLEEVE_UV_PX),(right_leg, _RIGHT_LEG_BASE_UV_PX),(right_pants, _RIGHT_LEG_PANTS_UV_PX),(left_leg, _LEFT_LEG_BASE_UV_PX),(left_pants, _LEFT_LEG_PANTS_UV_PX)):
        _append_unit_cube_rows(skin_buffers, model, uv_map)

    return PlayerModelPose(skin_face_rows=_rows_from_buffers(skin_buffers), held_block_pose=held_block_pose, special_item_face_rows=special_item_face_rows, visible_special_item_icon=visible_special_item_icon, shadow_rows=shadow_rows)