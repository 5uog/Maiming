# FILE: src/maiming/infrastructure/rendering/opengl/_internal/scene/player_model_pose.py
from __future__ import annotations
from dataclasses import dataclass
import math

import numpy as np

from ...facade.player_render_state import PlayerRenderState

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

def _clampf(x: float, lo: float, hi: float) -> float:
    v = float(x)
    if v < float(lo):
        return float(lo)
    if v > float(hi):
        return float(hi)
    return float(v)

def _lerp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)

def _mat_identity() -> np.ndarray:
    return np.identity(4, dtype=np.float32)

def _mat_translate(x: float, y: float, z: float) -> np.ndarray:
    m = _mat_identity()
    m[0, 3] = float(x)
    m[1, 3] = float(y)
    m[2, 3] = float(z)
    return m

def _mat_scale(x: float, y: float, z: float) -> np.ndarray:
    m = _mat_identity()
    m[0, 0] = float(x)
    m[1, 1] = float(y)
    m[2, 2] = float(z)
    return m

def _mat_rot_x(rad: float) -> np.ndarray:
    c = float(math.cos(float(rad)))
    s = float(math.sin(float(rad)))
    m = _mat_identity()
    m[1, 1] = c
    m[1, 2] = -s
    m[2, 1] = s
    m[2, 2] = c
    return m

def _mat_rot_y(rad: float) -> np.ndarray:
    c = float(math.cos(float(rad)))
    s = float(math.sin(float(rad)))
    m = _mat_identity()
    m[0, 0] = c
    m[0, 2] = s
    m[2, 0] = -s
    m[2, 2] = c
    return m

def _mat_rot_z(rad: float) -> np.ndarray:
    c = float(math.cos(float(rad)))
    s = float(math.sin(float(rad)))
    m = _mat_identity()
    m[0, 0] = c
    m[0, 1] = -s
    m[1, 0] = s
    m[1, 1] = c
    return m

def _compose(*mats: np.ndarray) -> np.ndarray:
    out = _mat_identity()
    for m in mats:
        out = (out @ m).astype(np.float32)
    return out

def _as_rows(m: np.ndarray) -> np.ndarray:
    return np.asarray(m, dtype=np.float32).reshape(16)

def _build_part_rows(state: PlayerRenderState) -> tuple[np.ndarray, ...]:
    crouch = _clampf(float(state.crouch_amount), 0.0, 1.0)

    body_yaw = math.radians(float(state.body_yaw_deg))
    head_yaw = math.radians(float(state.head_yaw_deg))
    head_pitch = math.radians(float(state.head_pitch_deg))

    phase = float(state.limb_phase_rad)
    swing = max(0.0, float(state.limb_swing_amount))

    walk_l = math.sin(float(phase))
    walk_r = math.sin(float(phase) + math.pi)

    arm_sway = float(_clampf(float(swing) / 0.5 if float(swing) > 1e-9 else 0.0, 0.0, 1.0)) * float(_ARM_SWAY_Z)

    right_arm_rot_x = float(swing) * float(walk_l) + float(_CROUCH_ARM_ROT_X) * float(crouch)
    left_arm_rot_x = float(swing) * float(walk_r) + float(_CROUCH_ARM_ROT_X) * float(crouch)

    right_arm_rot_z = -(float(arm_sway) + float(_CROUCH_ARM_ROT_Z) * float(crouch))
    left_arm_rot_z = float(arm_sway) + float(_CROUCH_ARM_ROT_Z) * float(crouch)

    right_leg_rot_x = float(swing) * float(walk_r)
    left_leg_rot_x = float(swing) * float(walk_l)

    root = _compose(_mat_translate(float(state.base_x), float(state.base_y), float(state.base_z)), _mat_rot_y(float(body_yaw)), _mat_translate(0.0, float(_MODEL_FEET_OFFSET_Y), 0.0))

    head_group_y = _lerp(float(_HEAD_GROUP_POS[1]), float(_CROUCH_HEAD_POS_Y), float(crouch))
    body_group_y = _lerp(float(_BODY_GROUP_POS_STAND[1]), float(_CROUCH_BODY_POS_Y), float(crouch))
    body_group_z = _lerp(0.0, float(_CROUCH_BODY_POS_Z), float(crouch))

    arm_group_y = _lerp(float(_RIGHT_ARM_GROUP_POS_STAND[1]), float(_CROUCH_ARM_POS_Y), float(crouch))
    arm_group_z = _lerp(0.0, float(_CROUCH_ARM_POS_Z), float(crouch))

    leg_group_z = _lerp(0.0, float(_CROUCH_LEG_POS_Z), float(crouch))

    head = _compose(root, _mat_translate(0.0, float(head_group_y), 0.0), _mat_rot_y(float(head_yaw)), _mat_rot_x(float(head_pitch)), _mat_translate(float(_HEAD_CENTER[0]), float(_HEAD_CENTER[1]), float(_HEAD_CENTER[2])), _mat_scale(float(_HEAD_SIZE[0]), float(_HEAD_SIZE[1]), float(_HEAD_SIZE[2])))

    body = _compose(root, _mat_translate(0.0, float(body_group_y), float(body_group_z)), _mat_rot_x(float(_CROUCH_BODY_ROT_X) * float(crouch)), _mat_scale(float(_BODY_SIZE[0]), float(_BODY_SIZE[1]), float(_BODY_SIZE[2])))

    right_arm = _compose(root, _mat_translate(float(_RIGHT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), _mat_rot_z(float(right_arm_rot_z)), _mat_rot_x(float(right_arm_rot_x)), _mat_translate(float(_RIGHT_ARM_PIVOT_SLIM[0]), float(_RIGHT_ARM_PIVOT_SLIM[1]), float(_RIGHT_ARM_PIVOT_SLIM[2])), _mat_scale(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))

    left_arm = _compose(root, _mat_translate(float(_LEFT_ARM_GROUP_POS_STAND[0]), float(arm_group_y), float(arm_group_z)), _mat_rot_z(float(left_arm_rot_z)), _mat_rot_x(float(left_arm_rot_x)), _mat_translate(float(_LEFT_ARM_PIVOT_SLIM[0]), float(_LEFT_ARM_PIVOT_SLIM[1]), float(_LEFT_ARM_PIVOT_SLIM[2])), _mat_scale(float(_ARM_SIZE_SLIM[0]), float(_ARM_SIZE_SLIM[1]), float(_ARM_SIZE_SLIM[2])))

    right_leg = _compose(root, _mat_translate(float(_RIGHT_LEG_GROUP_POS_STAND[0]), float(_RIGHT_LEG_GROUP_POS_STAND[1]), float(leg_group_z)), _mat_rot_x(float(right_leg_rot_x)), _mat_translate(float(_LEG_PIVOT[0]), float(_LEG_PIVOT[1]), float(_LEG_PIVOT[2])), _mat_scale(float(_LEG_SIZE[0]), float(_LEG_SIZE[1]), float(_LEG_SIZE[2])))

    left_leg = _compose(root, _mat_translate(float(_LEFT_LEG_GROUP_POS_STAND[0]), float(_LEFT_LEG_GROUP_POS_STAND[1]), float(leg_group_z)), _mat_rot_x(float(left_leg_rot_x)), _mat_translate(float(_LEG_PIVOT[0]), float(_LEG_PIVOT[1]), float(_LEG_PIVOT[2])), _mat_scale(float(_LEG_SIZE[0]), float(_LEG_SIZE[1]), float(_LEG_SIZE[2])))

    return (_as_rows(head), _as_rows(body), _as_rows(right_arm), _as_rows(left_arm), _as_rows(right_leg), _as_rows(left_leg))

def build_player_model_pose(state: PlayerRenderState | None) -> PlayerModelPose:
    empty = np.zeros((0, 16), dtype=np.float32)
    if state is None:
        return PlayerModelPose(world_rows=empty, shadow_rows=empty)

    rows = _build_part_rows(state)
    shadow_rows = np.ascontiguousarray(np.vstack(rows), dtype=np.float32)

    if bool(state.is_first_person):
        world_rows = np.ascontiguousarray(np.vstack(rows[1:]), dtype=np.float32)
    else:
        world_rows = shadow_rows

    return PlayerModelPose(world_rows=world_rows, shadow_rows=shadow_rows)