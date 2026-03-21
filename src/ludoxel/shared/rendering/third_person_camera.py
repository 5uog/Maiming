# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from ...application.runtime.state.camera_perspective import CAMERA_PERSPECTIVE_FIRST_PERSON, CAMERA_PERSPECTIVE_THIRD_PERSON_BACK, normalize_camera_perspective

from ..blocks.models.api import collision_aabbs_for_block
from ..blocks.registry.block_registry import BlockRegistry
from ..math.geometry.ray import Ray
from ..math.geometry.ray_aabb import ray_aabb_face
from ..math.vec3 import Vec3
from ..math.view_angles import forward_from_yaw_pitch_deg, yaw_pitch_deg_from_forward
from ..math.voxel.voxel_dda import dda_grid_traverse
from ..world.world_state import WorldState

_THIRD_PERSON_DISTANCE = 4.0
_THIRD_PERSON_COLLISION_MARGIN = 0.16

def resolve_camera(*, world: WorldState, block_registry: BlockRegistry, anchor_eye: Vec3, yaw_deg: float, pitch_deg: float, perspective: str) -> tuple[Vec3, float, float, Vec3]:
    normalized_perspective = normalize_camera_perspective(perspective)
    forward = forward_from_yaw_pitch_deg(float(yaw_deg), float(pitch_deg))
    if normalized_perspective == CAMERA_PERSPECTIVE_FIRST_PERSON:
        return (anchor_eye, float(yaw_deg), float(pitch_deg), forward)

    offset_sign = -1.0 if normalized_perspective == CAMERA_PERSPECTIVE_THIRD_PERSON_BACK else 1.0
    desired_eye = anchor_eye + forward * (float(_THIRD_PERSON_DISTANCE) * float(offset_sign))
    resolved_eye = _resolve_camera_collision(world=world, block_registry=block_registry, anchor_eye=anchor_eye, desired_eye=desired_eye, collision_margin=float(_THIRD_PERSON_COLLISION_MARGIN))

    if normalized_perspective == CAMERA_PERSPECTIVE_THIRD_PERSON_BACK:
        return (resolved_eye, float(yaw_deg), float(pitch_deg), forward)

    look_direction = (anchor_eye - resolved_eye).normalized()
    if look_direction.length() <= 1e-6:
        look_direction = Vec3(-float(forward.x), -float(forward.y), -float(forward.z)).normalized()
    look_yaw_deg, look_pitch_deg = yaw_pitch_deg_from_forward(look_direction)
    return (resolved_eye, float(look_yaw_deg), float(look_pitch_deg), look_direction)

def _resolve_camera_collision(*, world: WorldState, block_registry: BlockRegistry, anchor_eye: Vec3, desired_eye: Vec3, collision_margin: float) -> Vec3:
    delta = desired_eye - anchor_eye
    max_distance = float(delta.length())
    if max_distance <= 1e-6:
        return desired_eye

    direction = delta.normalized()
    ray = Ray(origin=anchor_eye + direction * 1e-4, direction=direction)

    def get_state(x: int, y: int, z: int) -> str | None:
        return world.blocks.get((int(x), int(y), int(z)))

    hit_distance: float | None = None
    for hit in dda_grid_traverse(origin=ray.origin, direction=direction, t_max=float(max_distance), cell_size=1.0):
        cx, cy, cz = int(hit.cell_x), int(hit.cell_y), int(hit.cell_z)
        state_str = world.blocks.get((int(cx), int(cy), int(cz)))
        if state_str is None:
            continue
        for aabb in collision_aabbs_for_block(str(state_str), get_state, block_registry.get, int(cx), int(cy), int(cz)):
            ray_hit = ray_aabb_face(ray, aabb)
            if ray_hit is None:
                continue
            enter_t = float(ray_hit.t_enter)
            if enter_t < 0.0 or enter_t > float(max_distance):
                continue
            if hit_distance is None or enter_t < float(hit_distance):
                hit_distance = float(enter_t)

    if hit_distance is None:
        return desired_eye

    resolved_distance = max(0.0, float(hit_distance) - float(collision_margin))
    return anchor_eye + direction * float(resolved_distance)