# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/session/session_manager.py
from __future__ import annotations

from dataclasses import dataclass, field
import math

from ...core.math.vec3 import Vec3, clampf
from ...core.math.smoothing import exp_alpha

from ...domain.world.world_state import WorldState
from ...domain.world.world_gen import generate_test_map
from ...domain.entities.player_entity import PlayerEntity
from ...domain.systems.movement_system import MoveInput, step_bedrock, step_flying, wish_dir_from_input
from ...domain.systems.collision_system import integrate_with_collisions, can_auto_jump_one_block, support_block_beneath

from ...domain.blocks.block_registry import BlockRegistry
from ...domain.blocks.default_registry import create_default_registry

from .session_settings import SessionSettings
from .render_snapshot import CameraDTO, PlayerModelSnapshotDTO, RenderSnapshotDTO
from ..services.interaction_service import InteractionService

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
    _sim_time_s: float = field(default=0.0, init=False, repr=False)
    _last_jump_press_s: float | None = field(default=None, init=False, repr=False)
    _player_walk_phase_rad: float = field(default=0.0, init=False, repr=False)
    _player_walk_phase_total_rad: float = field(default=0.0, init=False, repr=False)
    _airborne_start_y: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.interaction = InteractionService.create(world=self.world, player=self.player, block_registry=self.block_registry)

    @staticmethod
    def create_default(seed: int=0) -> "SessionManager":
        st = SessionSettings(seed=seed)
        world = generate_test_map(seed=seed)
        player = PlayerEntity(position=Vec3(float(st.spawn_x), float(st.spawn_y), float(st.spawn_z)), velocity=Vec3(0.0, 0.0, 0.0), yaw_deg=0.0, pitch_deg=0.0)
        return SessionManager(settings=st, world=world, player=player, block_registry=create_default_registry())

    def respawn(self) -> None:
        p = self.player
        p.position = Vec3(float(self.settings.spawn_x), float(self.settings.spawn_y), float(self.settings.spawn_z))
        p.velocity = Vec3(0.0, 0.0, 0.0)
        p.yaw_deg = 0.0
        p.pitch_deg = 0.0
        p.on_ground = False
        p.flying = False

        p.crouch_eye_offset = 0.0
        p.step_eye_offset = 0.0
        p.hold_jump_queued = False
        p.auto_jump_pending = False
        p.auto_jump_start_y = float(p.position.y)
        p.auto_jump_cooldown_s = 0.0
        self._last_jump_press_s = None
        self._player_walk_phase_rad = 0.0
        self._player_walk_phase_total_rad = 0.0
        self._airborne_start_y = None

    def _update_crouch_eye(self, dt: float, crouch: bool) -> None:
        p = self.player
        target = float(p.crouch_eye_drop) if bool(crouch) else 0.0
        cur = float(p.crouch_eye_offset)

        rate = 18.0
        a = exp_alpha(rate, float(dt))

        nxt = cur + (target - cur) * a
        nxt = max(0.0, min(float(p.crouch_eye_drop), float(nxt)))
        p.crouch_eye_offset = float(nxt)

    def _update_step_eye(self, dt: float) -> None:
        p = self.player
        cur = float(p.step_eye_offset)
        if abs(cur) <= 1e-6:
            p.step_eye_offset = 0.0
            return

        rate = 18.0
        a = exp_alpha(rate, float(dt))

        nxt = cur + (0.0 - cur) * a
        if abs(nxt) <= 1e-6:
            nxt = 0.0
        p.step_eye_offset = float(nxt)

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
        p = self.player
        speed = math.hypot(float(p.velocity.x), float(p.velocity.z))
        if speed <= 1e-6:
            return False

        base = max(1e-6, float(self.settings.movement.walk_speed))
        rate = float(_PLAYER_WALK_PHASE_RATE_AT_WALK_SPEED) * (float(speed) / float(base))
        prev_total = float(self._player_walk_phase_total_rad)
        self._player_walk_phase_total_rad = float(prev_total + rate * float(dt))
        self._player_walk_phase_rad = float(self._player_walk_phase_total_rad % (2.0 * math.pi))

        if bool(p.flying) or (not bool(p.on_ground)) or speed < float(_PLAYER_FOOTSTEP_MIN_SPEED):
            return False
        return int(math.floor(prev_total / math.pi)) != int(math.floor(float(self._player_walk_phase_total_rad) / math.pi))

    def _support_contact(self) -> tuple[str | None, tuple[int, int, int] | None]:
        contact = support_block_beneath(self.player, self.world, block_registry=self.block_registry, params=self.settings.collision)
        if contact is None:
            return (None, None)
        return (str(contact.block_state), tuple(int(v) for v in contact.cell))

    def step(self, dt: float, move_f: float, move_s: float, jump_held: bool, jump_pressed: bool, sprint: bool, crouch: bool, mdx: float, mdy: float, creative_mode: bool, auto_jump_enabled: bool) -> SessionStepResult:
        self._sim_time_s += float(dt)

        prev_on_ground = bool(self.player.on_ground)
        prev_vy = float(self.player.velocity.y)
        prev_pos_y = float(self.player.position.y)

        yaw_delta = (-float(mdx)) * float(self.settings.mouse_sens_deg_per_px)
        pitch_delta = (float(mdy)) * float(self.settings.mouse_sens_deg_per_px)

        self._update_creative_flight_toggle(creative_mode=bool(creative_mode), jump_pressed=bool(jump_pressed))

        if not bool(jump_held):
            self.player.hold_jump_queued = False

        if bool(self.player.flying):
            mi = MoveInput(forward=clampf(move_f, -1.0, 1.0), strafe=clampf(move_s, -1.0, 1.0), sprint=bool(sprint), crouch=bool(crouch), jump_pulse=False, jump_held=bool(jump_held), yaw_delta_deg=float(yaw_delta), pitch_delta_deg=float(pitch_delta))

            step_flying(self.player, mi, float(dt), params=self.settings.movement)
            integrate_with_collisions(self.player, self.world, float(dt), block_registry=self.block_registry, params=self.settings.collision, crouch=False, jump_pressed=False, flying=True)

            self.player.hold_jump_queued = False
            self.player.auto_jump_pending = False
            self._airborne_start_y = None

            self._update_crouch_eye(float(dt), False)
            self._update_step_eye(float(dt))
            self._update_player_walk_phase(float(dt))
            support_state, support_position = self._support_contact()
            return SessionStepResult(
                jump_started=False,
                landed=False,
                footstep_triggered=False,
                support_block_state=support_state,
                support_position=support_position,
                fall_distance_blocks=None,
            )

        jump_pulse = False

        if bool(self.player.on_ground) and bool(jump_pressed):
            jump_pulse = True
        elif bool(self.player.on_ground) and bool(self.player.hold_jump_queued) and bool(jump_held):
            jump_pulse = True
            self.player.hold_jump_queued = False
        else:
            if bool(auto_jump_enabled) and (not bool(jump_held)) and bool(self.player.on_ground):
                cd = float(self.player.auto_jump_cooldown_s)
                if cd > 0.0:
                    self.player.auto_jump_cooldown_s = max(0.0, cd - float(dt))
                else:
                    f = clampf(move_f, -1.0, 1.0)
                    s = clampf(move_s, -1.0, 1.0)
                    if abs(float(f)) + abs(float(s)) > 1e-6:
                        wish = wish_dir_from_input(self.player, f, s)
                        probe = float(self.settings.movement.auto_jump_probe)
                        dx = float(wish.x) * probe
                        dz = float(wish.z) * probe

                        if can_auto_jump_one_block(self.player, self.world, dx=dx, dz=dz, block_registry=self.block_registry, params=self.settings.collision):
                            jump_pulse = True
                            self.player.auto_jump_pending = True
                            self.player.auto_jump_start_y = float(self.player.position.y)

        mi = MoveInput(forward=clampf(move_f, -1.0, 1.0), strafe=clampf(move_s, -1.0, 1.0), sprint=bool(sprint), crouch=bool(crouch), jump_pulse=bool(jump_pulse), jump_held=bool(jump_held), yaw_delta_deg=float(yaw_delta), pitch_delta_deg=float(pitch_delta))

        step_bedrock(self.player, mi, float(dt), params=self.settings.movement)

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
            dy = float(self.player.position.y) - float(self.player.auto_jump_start_y)
            if dy >= float(self.settings.movement.auto_jump_success_dy):
                self.player.auto_jump_cooldown_s = float(self.settings.movement.auto_jump_cooldown_s)
            self.player.auto_jump_pending = False

        dy_corr = float(report.y_correction_dy)
        step_h = float(self.settings.collision.step_height)

        if (abs(dy_corr) > 1e-6 and abs(dy_corr) <= (step_h + 1e-3) and bool(report.supported_before) and bool(report.supported_after) and (not bool(jump_pulse)) and abs(float(prev_vy)) <= 1e-6 and abs(float(self.player.velocity.y)) <= 1e-6):
            self.player.step_eye_offset = float(self.player.step_eye_offset) - float(dy_corr)

        if bool(report.supported_after):
            self._airborne_start_y = None

        self._update_crouch_eye(float(dt), bool(crouch))
        self._update_step_eye(float(dt))
        footstep_triggered = self._update_player_walk_phase(float(dt))
        support_state, support_position = self._support_contact()
        return SessionStepResult(
            jump_started=bool(jump_pulse),
            landed=bool(landed_now),
            footstep_triggered=bool(footstep_triggered),
            support_block_state=support_state,
            support_position=support_position,
            fall_distance_blocks=fall_distance_blocks,
        )

    def make_snapshot(self, *, enable_view_bobbing: bool=True, enable_camera_shake: bool=True, view_bobbing_strength: float=0.35, camera_shake_strength: float=0.20) -> RenderSnapshotDTO:
        eye = self.player.eye_pos()
        # cam_shake_tx = 0.0
        # cam_shake_ty = 0.0
        cam_shake_tz = 0.0
        cam_shake_yaw_deg = 0.0
        # cam_shake_pitch_deg = 0.0
        # cam_shake_roll_deg = 0.0

        p = self.player
        speed = math.hypot(float(p.velocity.x), float(p.velocity.z))
        crouch_amount = 0.0
        if float(p.crouch_eye_drop) > 1e-9:
            crouch_amount = float(max(0.0, min(1.0, float(p.crouch_eye_offset) / float(p.crouch_eye_drop))))

        walk_speed = max(1e-6, float(self.settings.movement.walk_speed))
        speed_ratio = clampf(float(speed) / float(walk_speed), 0.0, float(_PLAYER_WALK_MAX_SWING_SCALE))
        limb_swing_amount = 0.5 * float(speed_ratio)

        bob = 0.5 * float(speed_ratio)
        if bool(p.flying):
            bob *= 0.40
        elif not bool(p.on_ground):
            bob *= 0.75

        phase = float(self._player_walk_phase_rad)
        s = math.sin(float(phase))
        c = math.cos(float(phase))
        pitch_wave = abs(math.cos(float(phase) - 0.2))
        step_eye_offset = float(p.step_eye_offset)
        view_bobbing_scale = clampf(float(view_bobbing_strength), 0.0, 1.0)
        camera_shake_scale = clampf(float(camera_shake_strength), 0.0, 1.0)

        fp_tx = float(s * bob * 0.08)
        fp_ty = float((-abs(c) * bob * 0.10) + step_eye_offset * 0.45)
        fp_tz = float(-abs(s) * bob * 0.03)
        fp_yaw_deg = float(s * bob * 1.25)
        fp_pitch_deg = float(pitch_wave * bob * 6.5)
        fp_roll_deg = float(s * bob * 4.0)

        cam_shake_tx = float(s * bob * 0.04)
        cam_shake_ty = float((-abs(c) * bob * 0.06) + step_eye_offset * 0.30)
        cam_shake_pitch_deg = float(pitch_wave * bob * 5.0)
        cam_shake_roll_deg = float(s * bob * 3.0)

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

        cam = CameraDTO(eye_x=eye.x, eye_y=eye.y, eye_z=eye.z, yaw_deg=self.player.yaw_deg, pitch_deg=self.player.pitch_deg, fov_deg=self.settings.fov_deg, shake_tx=float(cam_shake_tx), shake_ty=float(cam_shake_ty), shake_tz=float(cam_shake_tz), shake_yaw_deg=float(cam_shake_yaw_deg), shake_pitch_deg=float(cam_shake_pitch_deg), shake_roll_deg=float(cam_shake_roll_deg))

        player_model = PlayerModelSnapshotDTO(base_x=float(p.position.x), base_y=float(p.position.y), base_z=float(p.position.z), body_yaw_deg=float(p.yaw_deg), head_yaw_deg=0.0, head_pitch_deg=float(p.pitch_deg), limb_phase_rad=float(self._player_walk_phase_rad), limb_swing_amount=float(limb_swing_amount), crouch_amount=float(crouch_amount), first_person_tx=float(fp_tx), first_person_ty=float(fp_ty), first_person_tz=float(fp_tz), first_person_yaw_deg=float(fp_yaw_deg), first_person_pitch_deg=float(fp_pitch_deg), first_person_roll_deg=float(fp_roll_deg), is_first_person=True)

        return RenderSnapshotDTO(world_revision=int(self.world.revision), camera=cam, player_model=player_model)

    def break_block(self, reach: float=5.0, *, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.break_block(reach=float(reach), origin=origin, direction=direction)

    def place_block(self, block_id: str | None, reach: float=5.0, *, crouching: bool=False, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.place_block(block_id=block_id, reach=float(reach), crouching=bool(crouching), origin=origin, direction=direction)
