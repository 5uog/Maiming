# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
import math

from ....shared.blocks.registry.block_registry import BlockRegistry
from ....shared.math.scalars import clampf
from ....shared.systems.collision_system import can_auto_jump_one_block, integrate_with_collisions, support_block_beneath
from ....shared.systems.movement_system import MoveInput, step_bedrock, step_flying, wish_dir_from_input
from ....shared.world.entities.player_entity import PlayerEntity
from ....shared.world.world_state import WorldState
from ....shared.rendering.render_snapshot import PlayerModelSnapshotDTO
from ..state.session_settings import SessionSettings

PLAYER_WALK_PHASE_RATE_AT_WALK_SPEED = 8.0
PLAYER_WALK_MAX_SWING_SCALE = 1.35
PLAYER_FOOTSTEP_MIN_SPEED = 0.15
FALL_DAMAGE_SAFE_DISTANCE_BLOCKS = 3.0


@dataclass
class PlayerMotionState:
    walk_phase_rad: float = 0.0
    walk_phase_total_rad: float = 0.0
    airborne_start_y: float | None = None


@dataclass(frozen=True)
class PlayerStepInput:
    move_f: float
    move_s: float
    jump_held: bool
    jump_pressed: bool
    sprint: bool
    crouch: bool
    yaw_delta_deg: float
    pitch_delta_deg: float
    auto_jump_enabled: bool


@dataclass(frozen=True)
class RuntimePlayerStepResult:
    jump_started: bool
    landed: bool
    footstep_triggered: bool
    support_block_state: str | None
    support_position: tuple[int, int, int] | None
    fall_distance_blocks: float | None


def fall_damage_amount(*, fall_distance_blocks: float | None) -> float:
    if fall_distance_blocks is None:
        return 0.0
    distance = max(0.0, float(fall_distance_blocks))
    if distance <= float(FALL_DAMAGE_SAFE_DISTANCE_BLOCKS):
        return 0.0
    return float(math.ceil(float(distance) - float(FALL_DAMAGE_SAFE_DISTANCE_BLOCKS)))


def _update_crouch_eye(player: PlayerEntity, *, dt: float, crouch: bool) -> None:
    target = float(player.crouch_eye_drop) if bool(crouch) else 0.0
    current = float(player.crouch_eye_offset)
    alpha = 1.0 - math.exp(-18.0 * max(0.0, float(dt)))
    next_value = current + (target - current) * alpha
    next_value = max(0.0, min(float(player.crouch_eye_drop), float(next_value)))
    player.crouch_eye_offset = float(next_value)


def _update_step_eye(player: PlayerEntity, *, dt: float) -> None:
    current = float(player.step_eye_offset)
    if abs(current) <= 1e-6:
        player.step_eye_offset = 0.0
        return
    alpha = 1.0 - math.exp(-18.0 * max(0.0, float(dt)))
    next_value = current + (0.0 - current) * alpha
    if abs(next_value) <= 1e-6:
        next_value = 0.0
    player.step_eye_offset = float(next_value)


def _update_player_walk_phase(player: PlayerEntity, *, motion: PlayerMotionState, dt: float, walk_speed: float) -> bool:
    speed = math.hypot(float(player.velocity.x), float(player.velocity.z))
    if speed <= 1e-6:
        return False

    base = max(1e-6, float(walk_speed))
    rate = float(PLAYER_WALK_PHASE_RATE_AT_WALK_SPEED) * (float(speed) / float(base))
    previous_total = float(motion.walk_phase_total_rad)
    motion.walk_phase_total_rad = float(previous_total + rate * float(dt))
    motion.walk_phase_rad = float(motion.walk_phase_total_rad % (2.0 * math.pi))

    if bool(player.flying) or (not bool(player.on_ground)) or speed < float(PLAYER_FOOTSTEP_MIN_SPEED):
        return False
    return int(math.floor(previous_total / math.pi)) != int(math.floor(float(motion.walk_phase_total_rad) / math.pi))


def _support_contact(player: PlayerEntity, *, world: WorldState, block_registry: BlockRegistry, settings: SessionSettings) -> tuple[str | None, tuple[int, int, int] | None]:
    contact = support_block_beneath(player, world, block_registry=block_registry, params=settings.collision)
    if contact is None:
        return (None, None)
    return (str(contact.block_state), tuple(int(value) for value in contact.cell))


def advance_runtime_player(*, player: PlayerEntity, world: WorldState, block_registry: BlockRegistry, settings: SessionSettings, motion: PlayerMotionState, dt: float, control: PlayerStepInput) -> RuntimePlayerStepResult:
    player.advance_hurt_state(float(dt))

    prev_on_ground = bool(player.on_ground)
    prev_vy = float(player.velocity.y)
    prev_pos_y = float(player.position.y)

    player.yaw_deg += float(control.yaw_delta_deg)
    player.pitch_deg += float(control.pitch_delta_deg)
    player.clamp_pitch()

    if not bool(control.jump_held):
        player.hold_jump_queued = False

    if bool(player.flying):
        move_input = MoveInput(forward=clampf(control.move_f, -1.0, 1.0), strafe=clampf(control.move_s, -1.0, 1.0), sprint=bool(control.sprint), crouch=bool(control.crouch), jump_pulse=False, jump_held=bool(control.jump_held), yaw_delta_deg=0.0, pitch_delta_deg=0.0)
        step_flying(player, move_input, float(dt), params=settings.movement)
        integrate_with_collisions(player, world, float(dt), block_registry=block_registry, params=settings.collision, crouch=False, jump_pressed=False, flying=True)

        player.hold_jump_queued = False
        player.auto_jump_pending = False
        motion.airborne_start_y = None

        _update_crouch_eye(player, dt=float(dt), crouch=False)
        _update_step_eye(player, dt=float(dt))
        _update_player_walk_phase(player, motion=motion, dt=float(dt), walk_speed=float(settings.movement.walk_speed))
        support_state, support_position = _support_contact(player, world=world, block_registry=block_registry, settings=settings)
        return RuntimePlayerStepResult(jump_started=False, landed=False, footstep_triggered=False, support_block_state=support_state, support_position=support_position, fall_distance_blocks=None)

    jump_pulse = False
    if bool(player.on_ground) and bool(control.jump_pressed):
        jump_pulse = True
    elif bool(player.on_ground) and bool(player.hold_jump_queued) and bool(control.jump_held):
        jump_pulse = True
        player.hold_jump_queued = False
    elif bool(control.auto_jump_enabled) and (not bool(control.jump_held)) and bool(player.on_ground):
        cooldown = float(player.auto_jump_cooldown_s)
        if cooldown > 0.0:
            player.auto_jump_cooldown_s = max(0.0, cooldown - float(dt))
        else:
            forward = clampf(control.move_f, -1.0, 1.0)
            strafe = clampf(control.move_s, -1.0, 1.0)
            if abs(float(forward)) + abs(float(strafe)) > 1e-6:
                wish = wish_dir_from_input(player, forward, strafe)
                probe = float(settings.movement.auto_jump_probe)
                dx = float(wish.x) * probe
                dz = float(wish.z) * probe
                if can_auto_jump_one_block(player, world, dx=dx, dz=dz, block_registry=block_registry, params=settings.collision):
                    jump_pulse = True
                    player.auto_jump_pending = True
                    player.auto_jump_start_y = float(player.position.y)

    move_input = MoveInput(forward=clampf(control.move_f, -1.0, 1.0), strafe=clampf(control.move_s, -1.0, 1.0), sprint=bool(control.sprint), crouch=bool(control.crouch), jump_pulse=bool(jump_pulse), jump_held=bool(control.jump_held), yaw_delta_deg=0.0, pitch_delta_deg=0.0)
    step_bedrock(player, move_input, float(dt), params=settings.movement)
    report = integrate_with_collisions(player, world, float(dt), block_registry=block_registry, params=settings.collision, crouch=bool(control.crouch), jump_pressed=bool(jump_pulse), flying=False)

    if not bool(report.supported_after):
        if motion.airborne_start_y is None:
            motion.airborne_start_y = float(prev_pos_y)

    landed_now = (not prev_on_ground) and bool(report.supported_after) and (float(prev_vy) <= 0.0)
    fall_distance_blocks: float | None = None
    if bool(landed_now):
        start_y = float(prev_pos_y) if motion.airborne_start_y is None else float(motion.airborne_start_y)
        fall_distance_blocks = max(0.0, float(start_y) - float(player.position.y))

    if bool(landed_now) and bool(control.jump_held):
        player.hold_jump_queued = True

    if bool(landed_now) and bool(player.auto_jump_pending):
        delta_y = float(player.position.y) - float(player.auto_jump_start_y)
        if delta_y >= float(settings.movement.auto_jump_success_dy):
            player.auto_jump_cooldown_s = float(settings.movement.auto_jump_cooldown_s)
        player.auto_jump_pending = False

    delta_y_correction = float(report.y_correction_dy)
    step_height = float(settings.collision.step_height)
    if abs(delta_y_correction) > 1e-6 and abs(delta_y_correction) <= (step_height + 1e-3) and bool(report.supported_before) and bool(report.supported_after) and (not bool(jump_pulse)) and abs(float(prev_vy)) <= 1e-6 and abs(float(player.velocity.y)) <= 1e-6:
        player.step_eye_offset = float(player.step_eye_offset) - float(delta_y_correction)

    if bool(report.supported_after):
        motion.airborne_start_y = None

    _update_crouch_eye(player, dt=float(dt), crouch=bool(control.crouch))
    _update_step_eye(player, dt=float(dt))
    footstep_triggered = _update_player_walk_phase(player, motion=motion, dt=float(dt), walk_speed=float(settings.movement.walk_speed))
    support_state, support_position = _support_contact(player, world=world, block_registry=block_registry, settings=settings)
    return RuntimePlayerStepResult(jump_started=bool(jump_pulse), landed=bool(landed_now), footstep_triggered=bool(footstep_triggered), support_block_state=support_state, support_position=support_position, fall_distance_blocks=fall_distance_blocks)


def build_player_model_snapshot(*, player: PlayerEntity, motion: PlayerMotionState, walk_speed: float, is_first_person_view: bool) -> PlayerModelSnapshotDTO:
    speed = math.hypot(float(player.velocity.x), float(player.velocity.z))
    crouch_amount = 0.0
    if float(player.crouch_eye_drop) > 1e-9:
        crouch_amount = float(max(0.0, min(1.0, float(player.crouch_eye_offset) / float(player.crouch_eye_drop))))

    walk_speed_safe = max(1e-6, float(walk_speed))
    speed_ratio = clampf(float(speed) / float(walk_speed_safe), 0.0, float(PLAYER_WALK_MAX_SWING_SCALE))
    limb_swing_amount = 0.5 * float(speed_ratio)
    bob = 0.5 * float(speed_ratio)
    if bool(player.flying):
        bob *= 0.40
    elif not bool(player.on_ground):
        bob *= 0.75

    phase = float(motion.walk_phase_rad)
    sin_phase = math.sin(float(phase))
    cos_phase = math.cos(float(phase))
    pitch_wave = abs(math.cos(float(phase) - 0.2))
    step_eye_offset = float(player.step_eye_offset)

    fp_tx = float(sin_phase * bob * 0.08)
    fp_ty = float((-abs(cos_phase) * bob * 0.10) + step_eye_offset * 0.45)
    fp_tz = float(-abs(sin_phase) * bob * 0.03)
    fp_yaw_deg = float(sin_phase * bob * 1.25)
    fp_pitch_deg = float(pitch_wave * bob * 6.5)
    fp_roll_deg = float(sin_phase * bob * 4.0)

    return PlayerModelSnapshotDTO(base_x=float(player.position.x), base_y=float(player.position.y) + float(step_eye_offset), base_z=float(player.position.z), body_yaw_deg=float(player.yaw_deg), head_yaw_deg=0.0, head_pitch_deg=float(player.pitch_deg), limb_phase_rad=float(motion.walk_phase_rad), limb_swing_amount=float(limb_swing_amount), crouch_amount=float(crouch_amount), hurt_tint_strength=float(player.hurt_flash_strength()), first_person_tx=float(fp_tx), first_person_ty=float(fp_ty), first_person_tz=float(fp_tz), first_person_yaw_deg=float(fp_yaw_deg), first_person_pitch_deg=float(fp_pitch_deg), first_person_roll_deg=float(fp_roll_deg), is_first_person=bool(is_first_person_view))
