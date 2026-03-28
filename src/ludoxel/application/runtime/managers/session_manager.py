# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
import math

from ....shared.math.smoothing import exp_alpha
from ....shared.math.vec3 import Vec3
from ....shared.math.scalars import clampf
from ....shared.blocks.registry.block_registry import BlockRegistry
from ....shared.world.entities.player_entity import PlayerEntity
from ....shared.systems.collision_system import can_auto_jump_one_block, integrate_with_collisions, support_block_beneath
from ....shared.systems.gravity_system import GravitySystem
from ....shared.systems.movement_system import MoveInput, step_bedrock, step_flying, wish_dir_from_input
from ....shared.world.world_state import WorldState
from ....shared.rendering.render_snapshot import CameraDTO, FallingBlockRenderSampleDTO, PlayerModelSnapshotDTO, RenderSnapshotDTO
from ..state.session_settings import SessionSettings
from ....shared.systems.interaction_service import InteractionService

_FLIGHT_TOGGLE_WINDOW_S = 0.25
_PLAYER_WALK_PHASE_RATE_AT_WALK_SPEED = 8.0
_PLAYER_WALK_MAX_SWING_SCALE = 1.35
_PLAYER_FOOTSTEP_MIN_SPEED = 0.15


@dataclass(frozen=True)
class SessionStepResult:
    jump_started: bool
    landed: bool
    footstep_triggered: bool
    support_block_state: str | None
    support_position: tuple[int, int, int] | None
    fall_distance_blocks: float | None


@dataclass
class SessionManager:
    settings: SessionSettings
    world: WorldState
    player: PlayerEntity
    block_registry: BlockRegistry

    interaction: InteractionService = field(init=False, repr=False)
    gravity: GravitySystem = field(init=False, repr=False)
    _sim_time_s: float = field(default=0.0, init=False, repr=False)
    _last_jump_press_s: float | None = field(default=None, init=False, repr=False)
    _player_walk_phase_rad: float = field(default=0.0, init=False, repr=False)
    _player_walk_phase_total_rad: float = field(default=0.0, init=False, repr=False)
    _airborne_start_y: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.interaction = InteractionService.create(world=self.world, player=self.player, block_registry=self.block_registry)
        self.gravity = GravitySystem(block_registry=self.block_registry)

    def respawn(self) -> None:
        player = self.player
        player.position = Vec3(float(self.settings.spawn_x), float(self.settings.spawn_y), float(self.settings.spawn_z))
        player.velocity = Vec3(0.0, 0.0, 0.0)
        player.yaw_deg = 0.0
        player.pitch_deg = 0.0
        player.on_ground = False
        player.flying = False
        player.crouch_eye_offset = 0.0
        player.step_eye_offset = 0.0
        player.hold_jump_queued = False
        player.auto_jump_pending = False
        player.auto_jump_start_y = float(player.position.y)
        player.auto_jump_cooldown_s = 0.0
        player.fence_gate_overlap_exemption = None
        player.gravity_block_overlap_exemptions = ()
        self._last_jump_press_s = None
        self._player_walk_phase_rad = 0.0
        self._player_walk_phase_total_rad = 0.0
        self._airborne_start_y = None

    def _update_crouch_eye(self, dt: float, crouch: bool) -> None:
        player = self.player
        target = float(player.crouch_eye_drop) if bool(crouch) else 0.0
        current = float(player.crouch_eye_offset)

        rate = 18.0
        alpha = exp_alpha(rate, float(dt))

        next_value = current + (target - current) * alpha
        next_value = max(0.0, min(float(player.crouch_eye_drop), float(next_value)))
        player.crouch_eye_offset = float(next_value)

    def _update_step_eye(self, dt: float) -> None:
        player = self.player
        current = float(player.step_eye_offset)
        if abs(current) <= 1e-6:
            player.step_eye_offset = 0.0
            return

        rate = 18.0
        alpha = exp_alpha(rate, float(dt))

        next_value = current + (0.0 - current) * alpha
        if abs(next_value) <= 1e-6:
            next_value = 0.0
        player.step_eye_offset = float(next_value)

    def _update_creative_flight_toggle(self, *, creative_mode: bool, jump_pressed: bool) -> None:
        if not bool(creative_mode):
            self.player.flying = False
            self._last_jump_press_s = None
            return

        if not bool(jump_pressed):
            return

        now = float(self._sim_time_s)
        last = self._last_jump_press_s
        self._last_jump_press_s = float(now)

        if last is None:
            return

        if (float(now) - float(last)) > float(_FLIGHT_TOGGLE_WINDOW_S):
            return

        self.player.flying = not bool(self.player.flying)
        self._last_jump_press_s = None

        if bool(self.player.flying):
            self.player.velocity = Vec3(float(self.player.velocity.x), 0.0, float(self.player.velocity.z))
            self.player.on_ground = False
            self.player.hold_jump_queued = False
            self.player.auto_jump_pending = False
            self.player.auto_jump_cooldown_s = 0.0
            return

        self.player.velocity = Vec3(float(self.player.velocity.x), min(0.0, float(self.player.velocity.y)), float(self.player.velocity.z))

    def _update_player_walk_phase(self, dt: float) -> bool:
        player = self.player
        speed = math.hypot(float(player.velocity.x), float(player.velocity.z))
        if speed <= 1e-6:
            return False

        base = max(1e-6, float(self.settings.movement.walk_speed))
        rate = float(_PLAYER_WALK_PHASE_RATE_AT_WALK_SPEED) * (float(speed) / float(base))
        previous_total = float(self._player_walk_phase_total_rad)
        self._player_walk_phase_total_rad = float(previous_total + rate * float(dt))
        self._player_walk_phase_rad = float(self._player_walk_phase_total_rad % (2.0 * math.pi))

        if bool(player.flying) or (not bool(player.on_ground)) or speed < float(_PLAYER_FOOTSTEP_MIN_SPEED):
            return False
        return int(math.floor(previous_total / math.pi)) != int(math.floor(float(self._player_walk_phase_total_rad) / math.pi))

    def _support_contact(self) -> tuple[str | None, tuple[int, int, int] | None]:
        contact = support_block_beneath(self.player, self.world, block_registry=self.block_registry, params=self.settings.collision)
        if contact is None:
            return (None, None)
        return (str(contact.block_state), tuple(int(value) for value in contact.cell))

    def snapshot_world_blocks_for_persistence(self) -> dict[tuple[int, int, int], str]:
        return self.gravity.snapshot_blocks_for_persistence(self.world)

    def step(self, dt: float, move_f: float, move_s: float, jump_held: bool, jump_pressed: bool, sprint: bool, crouch: bool, mdx: float, mdy: float, creative_mode: bool, auto_jump_enabled: bool) -> SessionStepResult:
        self._sim_time_s += float(dt)
        self.gravity.step(self.world, float(dt), player=self.player)

        prev_on_ground = bool(self.player.on_ground)
        prev_vy = float(self.player.velocity.y)
        prev_pos_y = float(self.player.position.y)

        yaw_delta = (-float(mdx)) * float(self.settings.mouse_sens_deg_per_px)
        pitch_delta = float(mdy) * float(self.settings.mouse_sens_deg_per_px)

        self._update_creative_flight_toggle(creative_mode=bool(creative_mode), jump_pressed=bool(jump_pressed))

        if not bool(jump_held):
            self.player.hold_jump_queued = False

        if bool(self.player.flying):
            move_input = MoveInput(forward=clampf(move_f, -1.0, 1.0), strafe=clampf(move_s, -1.0, 1.0), sprint=bool(sprint), crouch=bool(crouch), jump_pulse=False, jump_held=bool(jump_held), yaw_delta_deg=float(yaw_delta), pitch_delta_deg=float(pitch_delta))

            step_flying(self.player, move_input, float(dt), params=self.settings.movement)
            integrate_with_collisions(self.player, self.world, float(dt), block_registry=self.block_registry, params=self.settings.collision, crouch=False, jump_pressed=False, flying=True)

            self.player.hold_jump_queued = False
            self.player.auto_jump_pending = False
            self._airborne_start_y = None

            self._update_crouch_eye(float(dt), False)
            self._update_step_eye(float(dt))
            self._update_player_walk_phase(float(dt))
            support_state, support_position = self._support_contact()
            return SessionStepResult(jump_started=False, landed=False, footstep_triggered=False, support_block_state=support_state, support_position=support_position, fall_distance_blocks=None)

        jump_pulse = False

        if bool(self.player.on_ground) and bool(jump_pressed):
            jump_pulse = True
        elif bool(self.player.on_ground) and bool(self.player.hold_jump_queued) and bool(jump_held):
            jump_pulse = True
            self.player.hold_jump_queued = False
        else:
            if bool(auto_jump_enabled) and (not bool(jump_held)) and bool(self.player.on_ground):
                cooldown = float(self.player.auto_jump_cooldown_s)
                if cooldown > 0.0:
                    self.player.auto_jump_cooldown_s = max(0.0, cooldown - float(dt))
                else:
                    forward = clampf(move_f, -1.0, 1.0)
                    strafe = clampf(move_s, -1.0, 1.0)
                    if abs(float(forward)) + abs(float(strafe)) > 1e-6:
                        wish = wish_dir_from_input(self.player, forward, strafe)
                        probe = float(self.settings.movement.auto_jump_probe)
                        dx = float(wish.x) * probe
                        dz = float(wish.z) * probe

                        if can_auto_jump_one_block(self.player, self.world, dx=dx, dz=dz, block_registry=self.block_registry, params=self.settings.collision):
                            jump_pulse = True
                            self.player.auto_jump_pending = True
                            self.player.auto_jump_start_y = float(self.player.position.y)

        move_input = MoveInput(forward=clampf(move_f, -1.0, 1.0), strafe=clampf(move_s, -1.0, 1.0), sprint=bool(sprint), crouch=bool(crouch), jump_pulse=bool(jump_pulse), jump_held=bool(jump_held), yaw_delta_deg=float(yaw_delta), pitch_delta_deg=float(pitch_delta))

        step_bedrock(self.player, move_input, float(dt), params=self.settings.movement)

        report = integrate_with_collisions(self.player, self.world, float(dt), block_registry=self.block_registry, params=self.settings.collision, crouch=bool(crouch), jump_pressed=bool(jump_pulse), flying=False)

        if not bool(report.supported_after):
            if self._airborne_start_y is None:
                self._airborne_start_y = float(prev_pos_y)

        landed_now = (not prev_on_ground) and bool(report.supported_after) and (float(prev_vy) <= 0.0)

        fall_distance_blocks: float | None = None
        if bool(landed_now):
            start_y = float(prev_pos_y) if self._airborne_start_y is None else float(self._airborne_start_y)
            fall_distance_blocks = max(0.0, float(start_y) - float(self.player.position.y))

        if bool(landed_now) and bool(jump_held):
            self.player.hold_jump_queued = True

        if bool(landed_now) and bool(self.player.auto_jump_pending):
            delta_y = float(self.player.position.y) - float(self.player.auto_jump_start_y)
            if delta_y >= float(self.settings.movement.auto_jump_success_dy):
                self.player.auto_jump_cooldown_s = float(self.settings.movement.auto_jump_cooldown_s)
            self.player.auto_jump_pending = False

        delta_y_correction = float(report.y_correction_dy)
        step_height = float(self.settings.collision.step_height)

        if (abs(delta_y_correction) > 1e-6 and abs(delta_y_correction) <= (step_height + 1e-3) and bool(report.supported_before) and bool(report.supported_after) and (not bool(jump_pulse)) and abs(float(prev_vy)) <= 1e-6 and abs(float(self.player.velocity.y)) <= 1e-6):
            self.player.step_eye_offset = float(self.player.step_eye_offset) - float(delta_y_correction)

        if bool(report.supported_after):
            self._airborne_start_y = None

        self._update_crouch_eye(float(dt), bool(crouch))
        self._update_step_eye(float(dt))
        footstep_triggered = self._update_player_walk_phase(float(dt))
        support_state, support_position = self._support_contact()
        return SessionStepResult(jump_started=bool(jump_pulse), landed=bool(landed_now), footstep_triggered=bool(footstep_triggered), support_block_state=support_state, support_position=support_position, fall_distance_blocks=fall_distance_blocks)

    def make_snapshot(self, *, enable_view_bobbing: bool=True, enable_camera_shake: bool=True, view_bobbing_strength: float=0.35, camera_shake_strength: float=0.20, is_first_person_view: bool=True) -> RenderSnapshotDTO:
        eye = self.player.eye_pos()
        cam_shake_tz = 0.0
        cam_shake_yaw_deg = 0.0

        player = self.player
        speed = math.hypot(float(player.velocity.x), float(player.velocity.z))
        crouch_amount = 0.0
        if float(player.crouch_eye_drop) > 1e-9:
            crouch_amount = float(max(0.0, min(1.0, float(player.crouch_eye_offset) / float(player.crouch_eye_drop))))

        walk_speed = max(1e-6, float(self.settings.movement.walk_speed))
        speed_ratio = clampf(float(speed) / float(walk_speed), 0.0, float(_PLAYER_WALK_MAX_SWING_SCALE))
        limb_swing_amount = 0.5 * float(speed_ratio)

        bob = 0.5 * float(speed_ratio)
        if bool(player.flying):
            bob *= 0.40
        elif not bool(player.on_ground):
            bob *= 0.75

        phase = float(self._player_walk_phase_rad)
        sin_phase = math.sin(float(phase))
        cos_phase = math.cos(float(phase))
        pitch_wave = abs(math.cos(float(phase) - 0.2))
        step_eye_offset = float(player.step_eye_offset)
        view_bobbing_scale = clampf(float(view_bobbing_strength), 0.0, 1.0)
        camera_shake_scale = clampf(float(camera_shake_strength), 0.0, 1.0)

        fp_tx = float(sin_phase * bob * 0.08)
        fp_ty = float((-abs(cos_phase) * bob * 0.10) + step_eye_offset * 0.45)
        fp_tz = float(-abs(sin_phase) * bob * 0.03)
        fp_yaw_deg = float(sin_phase * bob * 1.25)
        fp_pitch_deg = float(pitch_wave * bob * 6.5)
        fp_roll_deg = float(sin_phase * bob * 4.0)

        cam_shake_tx = float(sin_phase * bob * 0.04)
        cam_shake_ty = float((-abs(cos_phase) * bob * 0.06) + step_eye_offset * 0.30)
        cam_shake_pitch_deg = float(pitch_wave * bob * 5.0)
        cam_shake_roll_deg = float(sin_phase * bob * 3.0)

        fp_tx *= float(view_bobbing_scale)
        fp_ty *= float(view_bobbing_scale)
        fp_tz *= float(view_bobbing_scale)
        fp_yaw_deg *= float(view_bobbing_scale)
        fp_pitch_deg *= float(view_bobbing_scale)
        fp_roll_deg *= float(view_bobbing_scale)

        cam_shake_tx *= float(camera_shake_scale)
        cam_shake_ty *= float(camera_shake_scale)
        cam_shake_tz *= float(camera_shake_scale)
        cam_shake_yaw_deg *= float(camera_shake_scale)
        cam_shake_pitch_deg *= float(camera_shake_scale)
        cam_shake_roll_deg *= float(camera_shake_scale)

        if not bool(enable_view_bobbing):
            fp_tx = 0.0
            fp_ty = 0.0
            fp_tz = 0.0
            fp_yaw_deg = 0.0
            fp_pitch_deg = 0.0
            fp_roll_deg = 0.0

        if not bool(enable_camera_shake):
            cam_shake_tx = 0.0
            cam_shake_ty = 0.0
            cam_shake_tz = 0.0
            cam_shake_yaw_deg = 0.0
            cam_shake_pitch_deg = 0.0
            cam_shake_roll_deg = 0.0

        camera = CameraDTO(eye_x=eye.x, eye_y=eye.y, eye_z=eye.z, yaw_deg=self.player.yaw_deg, pitch_deg=self.player.pitch_deg, fov_deg=self.settings.fov_deg, shake_tx=float(cam_shake_tx), shake_ty=float(cam_shake_ty), shake_tz=float(cam_shake_tz), shake_yaw_deg=float(cam_shake_yaw_deg), shake_pitch_deg=float(cam_shake_pitch_deg), shake_roll_deg=float(cam_shake_roll_deg))

        player_model = PlayerModelSnapshotDTO(base_x=float(player.position.x), base_y=float(player.position.y) + float(step_eye_offset), base_z=float(player.position.z), body_yaw_deg=float(player.yaw_deg), head_yaw_deg=0.0, head_pitch_deg=float(player.pitch_deg), limb_phase_rad=float(self._player_walk_phase_rad), limb_swing_amount=float(limb_swing_amount), crouch_amount=float(crouch_amount), first_person_tx=float(fp_tx), first_person_ty=float(fp_ty), first_person_tz=float(fp_tz), first_person_yaw_deg=float(fp_yaw_deg), first_person_pitch_deg=float(fp_pitch_deg), first_person_roll_deg=float(fp_roll_deg), is_first_person=bool(is_first_person_view))

        falling_blocks = tuple(FallingBlockRenderSampleDTO(state_str=str(sample.state_str), x=float(sample.x), y=float(sample.y), z=float(sample.z)) for sample in self.gravity.render_samples())
        return RenderSnapshotDTO(world_revision=int(self.world.revision), camera=camera, player_model=player_model, falling_blocks=falling_blocks)

    def break_block(self, reach: float=5.0, *, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.break_block(reach=float(reach), origin=origin, direction=direction)

    def place_block(self, block_id: str | None, reach: float=5.0, *, crouching: bool=False, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.place_block(block_id=block_id, reach=float(reach), crouching=bool(crouching), origin=origin, direction=direction)
