# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

from ..math.scalars import clampf
from .first_person_geometry import THIRD_PERSON_RIGHT_HAND_ANCHOR, build_third_person_item_hand_transform, cube_rows_from_boxes, held_block_model_boxes_for_kind
from ..math.transform_matrices import compose_matrices, rotate_x_rad_matrix, rotate_y_rad_matrix, rotate_z_rad_matrix, scale_matrix, translate_matrix
from .player_render_state import PlayerRenderState

_PX = 1.0 / 16.0
_HEAD_SIZE = (8.0 * _PX, 8.0 * _PX, 8.0 * _PX)
_BODY_SIZE = (8.0 * _PX, 12.0 * _PX, 4.0 * _PX)
_ARM_SIZE_SLIM = (3.0 * _PX, 12.0 * _PX, 4.0 * _PX)
_LEG_SIZE = (4.0 * _PX, 12.0 * _PX, 4.0 * _PX)
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

@dataclass(frozen=True)
class PlayerModelPose:
    world_rows: np.ndarray
    shadow_rows: np.ndarray

def _lerp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)

def _as_rows(m: np.ndarray) -> np.ndarray:
    return np.asarray(m, dtype=np.float32).reshape(16)

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

def _build_part_rows(state: PlayerRenderState) -> tuple[np.ndarray, ...]:
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
    left_arm_rot_x = float(swing) * float(walk_r) + float(_CROUCH_ARM_ROT_X) * float(crouch)
    right_arm_rot_z = -(float(arm_sway) + float(_CROUCH_ARM_ROT_Z) * float(crouch))
    left_arm_rot_z = float(arm_sway) + float(_CROUCH_ARM_ROT_Z) * float(crouch)
    right_leg_rot_x = float(swing) * float(walk_r)
    left_leg_rot_x = float(swing) * float(walk_l)
    root = compose_matrices(translate_matrix(float(state.base_x), float(state.base_y), float(state.base_z)), rotate_y_rad_matrix(float(body_yaw)), translate_matrix(0.0, float(_MODEL_FEET_OFFSET_Y), 0.0))
    head_group_y = _lerp(float(_HEAD_GROUP_POS[1]), float(_CROUCH_HEAD_POS_Y), float(crouch))
    body_group_y = _lerp(float(_BODY_GROUP_POS_STAND[1]), float(_CROUCH_BODY_POS_Y), float(crouch))
    body_group_z = _lerp(0.0, float(_CROUCH_BODY_POS_Z), float(crouch))
    arm_group_y = _lerp(float(_RIGHT_ARM_GROUP_POS_STAND[1]), float(_CROUCH_ARM_POS_Y), float(crouch))
    arm_group_z = _lerp(0.0, float(_CROUCH_ARM_POS_Z), float(crouch))
    leg_group_z = _lerp(0.0, float(_CROUCH_LEG_POS_Z), float(crouch))
    head = compose_matrices(root, translate_matrix(0.0, float(head_group_y), 0.0), rotate_y_rad_matrix(float(head_yaw)), rotate_x_rad_matrix(float(head_pitch)), translate_matrix(float(_HEAD_CENTER[0]), float(_HEAD_CENTER[1]), float(_HEAD_CENTER[2])), scale_matrix(float(_HEAD_SIZE[0]), float(_HEAD_SIZE[1]), float(_HEAD_SIZE[2])))
    body = compose_matrices(root, translate_matrix(0.0, float(body_group_y), float(body_group_z)), rotate_x_rad_matrix(float(_CROUCH_BODY_ROT_X) * float(crouch)), scale_matrix(float(_BODY_SIZE[0]), float(_BODY_SIZE[1]), float(_BODY_SIZE[2])))
    right_arm_parent = compose_matrices(root, translate_matrix(float(_RIGHT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), rotate_z_rad_matrix(float(right_arm_rot_z)), rotate_x_rad_matrix(float(right_arm_rot_x)))
    left_arm_parent = compose_matrices(root, translate_matrix(float(_LEFT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), rotate_z_rad_matrix(float(left_arm_rot_z)), rotate_x_rad_matrix(float(left_arm_rot_x)))
    right_arm = compose_matrices(right_arm_parent, translate_matrix(float(_RIGHT_ARM_PIVOT_SLIM[0]), float(_RIGHT_ARM_PIVOT_SLIM[1]), float(_RIGHT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))
    left_arm = compose_matrices(left_arm_parent, translate_matrix(float(_LEFT_ARM_PIVOT_SLIM[0]), float(_LEFT_ARM_PIVOT_SLIM[1]), float(_LEFT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))
    right_leg = compose_matrices(root, translate_matrix(float(_RIGHT_LEG_GROUP_POS_STAND[0]), float(_RIGHT_LEG_GROUP_POS_STAND[1]), float(leg_group_z)), rotate_x_rad_matrix(float(right_leg_rot_x)), translate_matrix(float(_LEG_PIVOT[0]), float(_LEG_PIVOT[1]), float(_LEG_PIVOT[2])), scale_matrix(float(_LEG_SIZE[0]), float(_LEG_SIZE[1]), float(_LEG_SIZE[2])))
    left_leg = compose_matrices(root, translate_matrix(float(_LEFT_LEG_GROUP_POS_STAND[0]), float(_LEFT_LEG_GROUP_POS_STAND[1]), float(leg_group_z)), rotate_x_rad_matrix(float(left_leg_rot_x)), translate_matrix(float(_LEG_PIVOT[0]), float(_LEG_PIVOT[1]), float(_LEG_PIVOT[2])), scale_matrix(float(_LEG_SIZE[0]), float(_LEG_SIZE[1]), float(_LEG_SIZE[2])))

    rows = [_as_rows(head), _as_rows(body), _as_rows(right_arm), _as_rows(left_arm), _as_rows(right_leg), _as_rows(left_leg)]

    first_person = state.first_person
    if bool(state.is_first_person) and first_person is not None:
        attack_x, attack_y, attack_z = _shadow_attack_angles(float(first_person.swing_progress))
        left_arm_shadow_parent = compose_matrices(root, translate_matrix(float(_LEFT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), rotate_z_rad_matrix(float(left_arm_rot_z) - float(attack_z)), rotate_y_rad_matrix(float(-attack_y)), rotate_x_rad_matrix(float(left_arm_rot_x) + float(attack_x)))
        left_arm_shadow = compose_matrices(left_arm_shadow_parent, translate_matrix(float(_LEFT_ARM_PIVOT_SLIM[0]), float(_LEFT_ARM_PIVOT_SLIM[1]), float(_LEFT_ARM_PIVOT_SLIM[2])), scale_matrix(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))
        rows[3] = _as_rows(left_arm_shadow)

        if first_person.visible_block_kind is not None:
            hand_anchor = compose_matrices(left_arm_shadow_parent, translate_matrix(float(THIRD_PERSON_RIGHT_HAND_ANCHOR[0]), float(THIRD_PERSON_RIGHT_HAND_ANCHOR[1]), float(THIRD_PERSON_RIGHT_HAND_ANCHOR[2])))
            item_parent = compose_matrices(hand_anchor, build_third_person_item_hand_transform())
            block_boxes = [tb.box for tb in held_block_model_boxes_for_kind(first_person.visible_block_kind)]
            block_rows = cube_rows_from_boxes(block_boxes, item_parent)
            if block_rows.size > 0:
                rows.extend([row for row in block_rows])

    return tuple(rows)

def build_player_model_pose(state: PlayerRenderState | None) -> PlayerModelPose:
    empty = np.zeros((0, 16), dtype=np.float32)
    if state is None:
        return PlayerModelPose(world_rows=empty, shadow_rows=empty)

    rows = _build_part_rows(state)
    shadow_rows = np.ascontiguousarray(np.vstack(rows), dtype=np.float32)

    if bool(state.is_first_person):
        world_rows = empty
    else:
        world_rows = shadow_rows

    return PlayerModelPose(world_rows=world_rows, shadow_rows=shadow_rows)