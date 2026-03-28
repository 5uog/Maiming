# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import random

from ..blocks.models.api import render_boxes_for_block
from ..math.vec3 import Vec3
from .faces.face_row_utils import uv_rect_from_pixels
from .render_types import DefLookup, UVLookup
from .render_snapshot import BlockBreakParticleRenderSampleDTO

_PARTICLE_SUBDIVISIONS_PER_BLOCK = 4.0
_PARTICLE_FRAGMENT_SIZE_PX = 4.0
_PARTICLE_MIN_SUBPIXEL_ORIGIN_PX = 0.0
_PARTICLE_MAX_SUBPIXEL_ORIGIN_PX = 12.0
_PARTICLE_GRAVITY = 12.0
_PARTICLE_DRAG = 0.88
_PARTICLE_MIN_SIZE = 0.08
_PARTICLE_MAX_SIZE = 0.12
_PARTICLE_MIN_LIFETIME_S = 0.55
_PARTICLE_MAX_LIFETIME_S = 0.80
_PARTICLE_BASE_SPEED = 1.7
_PARTICLE_HORIZONTAL_JITTER = 0.16
_PARTICLE_VERTICAL_JITTER_MIN = -0.03
_PARTICLE_VERTICAL_JITTER_MAX = 0.08
_PARTICLE_VERTICAL_BIAS_MIN = 0.08
_PARTICLE_VERTICAL_BIAS_MAX = 0.20


@dataclass(frozen=True)
class BlockBreakParticleState:
    position: Vec3
    velocity: Vec3
    size: float
    age_s: float
    lifetime_s: float
    uv_rect: tuple[float, float, float, float]


def _dominant_face_index(offset: Vec3) -> int:
    ax = abs(float(offset.x))
    ay = abs(float(offset.y))
    az = abs(float(offset.z))

    if ay >= ax and ay >= az:
        return 2 if float(offset.y) >= 0.0 else 3
    if ax >= az:
        return 0 if float(offset.x) >= 0.0 else 1
    return 4 if float(offset.z) >= 0.0 else 5


def _subdivisions(span: float) -> int:
    return max(1, int(math.ceil(max(0.0, float(span)) * float(_PARTICLE_SUBDIVISIONS_PER_BLOCK) - 1e-9)))


def _sample_coordinate(min_value: float, max_value: float) -> float:
    lower = float(min_value)
    upper = float(max_value)
    if abs(float(upper) - float(lower)) <= 1e-9:
        return 0.5 * (float(lower) + float(upper))
    return random.uniform(float(lower), float(upper))


def _scaled_particle_count(base_count: int, spawn_rate: float) -> int:
    scaled = max(0.0, float(base_count) * max(0.0, float(spawn_rate)))
    whole = int(math.floor(float(scaled) + 1e-9))
    if random.random() < float(scaled) - float(whole):
        whole += 1
    return max(0, int(whole))


def spawn_block_break_particles(*, state_str: str, cell: tuple[int, int, int], uv_lookup: UVLookup, def_lookup: DefLookup, spawn_rate: float=1.0, speed_scale: float=1.0) -> tuple[BlockBreakParticleState, ...]:
    boxes = tuple(render_boxes_for_block(str(state_str), lambda _x, _y, _z: None, def_lookup, 0, 0, 0))
    if not boxes:
        return ()

    cell_x = int(cell[0])
    cell_y = int(cell[1])
    cell_z = int(cell[2])
    density = max(0.0, float(spawn_rate))
    speed_multiplier = max(0.0, float(speed_scale))

    particles: list[BlockBreakParticleState] = []
    for box in boxes:
        span_x = float(box.mx_x) - float(box.mn_x)
        span_y = float(box.mx_y) - float(box.mn_y)
        span_z = float(box.mx_z) - float(box.mn_z)
        samples_x = _subdivisions(float(span_x))
        samples_y = _subdivisions(float(span_y))
        samples_z = _subdivisions(float(span_z))
        particle_count = _scaled_particle_count(int(samples_x * samples_y * samples_z), float(density))
        if particle_count <= 0:
            continue
        box_center = Vec3(float(cell_x) + 0.5 * (float(box.mn_x) + float(box.mx_x)), float(cell_y) + 0.5 * (float(box.mn_y) + float(box.mx_y)), float(cell_z) + 0.5 * (float(box.mn_z) + float(box.mx_z)))

        for _index in range(int(particle_count)):
            local_x = _sample_coordinate(float(box.mn_x), float(box.mx_x))
            local_y = _sample_coordinate(float(box.mn_y), float(box.mx_y))
            local_z = _sample_coordinate(float(box.mn_z), float(box.mx_z))
            position = Vec3(float(cell_x) + float(local_x), float(cell_y) + float(local_y), float(cell_z) + float(local_z))
            offset = position - box_center
            face_idx = _dominant_face_index(offset)
            texture_uv = uv_lookup(str(state_str), int(face_idx))
            px0 = random.uniform(float(_PARTICLE_MIN_SUBPIXEL_ORIGIN_PX), float(_PARTICLE_MAX_SUBPIXEL_ORIGIN_PX))
            py0 = random.uniform(float(_PARTICLE_MIN_SUBPIXEL_ORIGIN_PX), float(_PARTICLE_MAX_SUBPIXEL_ORIGIN_PX))
            uv_rect = uv_rect_from_pixels(texture_uv, (float(px0), float(py0), float(px0) + float(_PARTICLE_FRAGMENT_SIZE_PX), float(py0) + float(_PARTICLE_FRAGMENT_SIZE_PX)))
            jitter = Vec3(
                random.uniform(-float(_PARTICLE_HORIZONTAL_JITTER), float(_PARTICLE_HORIZONTAL_JITTER)),
                random.uniform(float(_PARTICLE_VERTICAL_JITTER_MIN), float(_PARTICLE_VERTICAL_JITTER_MAX)),
                random.uniform(-float(_PARTICLE_HORIZONTAL_JITTER), float(_PARTICLE_HORIZONTAL_JITTER)),
            )
            vertical_bias = random.uniform(float(_PARTICLE_VERTICAL_BIAS_MIN), float(_PARTICLE_VERTICAL_BIAS_MAX))
            velocity = Vec3(
                (float(offset.x) * float(_PARTICLE_BASE_SPEED) + float(jitter.x)) * float(speed_multiplier),
                (float(offset.y) * float(_PARTICLE_BASE_SPEED) + float(vertical_bias) + float(jitter.y)) * float(speed_multiplier),
                (float(offset.z) * float(_PARTICLE_BASE_SPEED) + float(jitter.z)) * float(speed_multiplier),
            )
            particles.append(BlockBreakParticleState(position=position, velocity=velocity, size=random.uniform(float(_PARTICLE_MIN_SIZE), float(_PARTICLE_MAX_SIZE)), age_s=0.0, lifetime_s=random.uniform(float(_PARTICLE_MIN_LIFETIME_S), float(_PARTICLE_MAX_LIFETIME_S)), uv_rect=uv_rect))

    return tuple(particles)


def advance_block_break_particles(particles: tuple[BlockBreakParticleState, ...], dt: float) -> tuple[BlockBreakParticleState, ...]:
    if not particles:
        return ()

    step_dt = max(0.0, float(dt))
    out: list[BlockBreakParticleState] = []
    for particle in particles:
        next_age = float(particle.age_s) + float(step_dt)
        if next_age >= float(particle.lifetime_s):
            continue
        velocity = Vec3(float(particle.velocity.x) * float(_PARTICLE_DRAG), (float(particle.velocity.y) - float(_PARTICLE_GRAVITY) * float(step_dt)) * float(_PARTICLE_DRAG), float(particle.velocity.z) * float(_PARTICLE_DRAG))
        position = particle.position + velocity * float(step_dt)
        out.append(replace(particle, position=position, velocity=velocity, age_s=float(next_age)))
    return tuple(out)


def render_samples_from_block_break_particles(particles: tuple[BlockBreakParticleState, ...]) -> tuple[BlockBreakParticleRenderSampleDTO, ...]:
    if not particles:
        return ()
    return tuple(BlockBreakParticleRenderSampleDTO(x=float(particle.position.x), y=float(particle.position.y), z=float(particle.position.z), size=float(particle.size), u0=float(particle.uv_rect[0]), v0=float(particle.uv_rect[1]), u1=float(particle.uv_rect[2]), v1=float(particle.uv_rect[3])) for particle in particles)
