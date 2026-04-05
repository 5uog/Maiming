# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
import math

from ....shared.math.scalars import clampf
from ....shared.math.vec3 import Vec3
from ....shared.blocks.registry.block_registry import BlockRegistry
from ....shared.world.entities.player_entity import PlayerEntity
from ....shared.systems.collision_system import SupportBlockContact, support_block_beneath
from ....shared.systems.gravity_system import GravityBrokenBlock, GravitySystem
from ....shared.systems.interaction_service import InteractionService
from ....shared.world.world_state import WorldState
from ....shared.rendering.render_snapshot import CameraDTO, FallingBlockRenderSampleDTO, RenderSnapshotDTO
from ..ai_player_types import AiPlayerState, AiSpawnEggSettings
from ..state.session_settings import SessionSettings
from .ai_player_manager import AiLocalAttackResult, AiPlayerManager, AiRoutePathSnapshot
from .player_combat import MELEE_ATTACK_REACH_BLOCKS, apply_void_damage, attack_sprinting
from .player_kinematics import PLAYER_WALK_MAX_SWING_SCALE, PlayerMotionState, PlayerStepInput, advance_runtime_player, build_player_model_snapshot, fall_damage_amount

_FLIGHT_TOGGLE_WINDOW_S = 0.25


@dataclass(frozen=True)
class SessionStepResult:
    jump_started: bool
    landed: bool
    footstep_triggered: bool
    support_block_state: str | None
    support_position: tuple[int, int, int] | None
    fall_distance_blocks: float | None
    damage_taken: float = 0.0
    death_reason: str | None = None
    gravity_broken_blocks: tuple[GravityBrokenBlock, ...] = ()
    play_damage_sound: bool = False
    ai_damage_sound_positions: tuple[tuple[float, float, float], ...] = ()


@dataclass
class SessionManager:
    settings: SessionSettings
    world: WorldState
    player: PlayerEntity
    block_registry: BlockRegistry

    interaction: InteractionService = field(init=False, repr=False)
    gravity: GravitySystem = field(init=False, repr=False)
    ai_players: AiPlayerManager = field(init=False, repr=False)
    _sim_time_s: float = field(default=0.0, init=False, repr=False)
    _last_jump_press_s: float | None = field(default=None, init=False, repr=False)
    _player_motion: PlayerMotionState = field(default_factory=PlayerMotionState, init=False, repr=False)
    _death_reason: str | None = field(default=None, init=False, repr=False)
    _void_damage_timer_s: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.player.clamp_health()
        self.interaction = InteractionService.create(world=self.world, player=self.player, block_registry=self.block_registry)
        self.gravity = GravitySystem(block_registry=self.block_registry)
        self.ai_players = AiPlayerManager(world=self.world, block_registry=self.block_registry, settings=self.settings)

    def shutdown(self) -> None:
        self.ai_players.shutdown()

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
        player.heal_to_full()
        self._last_jump_press_s = None
        self._player_motion = PlayerMotionState()
        self._death_reason = None
        self._void_damage_timer_s = 0.0

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

    def support_block_contact(self) -> SupportBlockContact | None:
        return support_block_beneath(self.player, self.world, block_registry=self.block_registry, params=self.settings.collision)

    def snapshot_world_blocks_for_persistence(self) -> dict[tuple[int, int, int], str]:
        return self.gravity.snapshot_blocks_for_persistence(self.world)

    def current_death_reason(self) -> str | None:
        if self.player.alive():
            return None
        return self._death_reason

    def set_ai_players(self, states: object) -> None:
        normalized_states: list[AiPlayerState] = []
        if isinstance(states, (list, tuple)):
            for state in states:
                if isinstance(state, AiPlayerState):
                    normalized_states.append(state.normalized())
        self.ai_players.load_states(tuple(normalized_states))

    def ai_states(self) -> tuple[AiPlayerState, ...]:
        return self.ai_players.actors()

    def spawn_ai_player(self, *, spawn_cell: tuple[int, int, int], settings: AiSpawnEggSettings) -> str | None:
        return self.ai_players.spawn_from_egg(spawn_cell=tuple(int(value) for value in spawn_cell), settings=settings.normalized())

    def ai_player_settings(self, actor_id: str) -> AiSpawnEggSettings | None:
        return self.ai_players.actor_settings(str(actor_id))

    def update_ai_player_settings(self, *, actor_id: str, settings: AiSpawnEggSettings) -> bool:
        return bool(self.ai_players.update_actor_settings(actor_id=str(actor_id), settings=settings.normalized()))

    def remove_ai_player(self, actor_id: str) -> bool:
        return bool(self.ai_players.remove_actor(str(actor_id)))

    def cancel_ai_navigation(self, actor_id: str) -> bool:
        return bool(self.ai_players.cancel_actor_navigation(str(actor_id)))

    def pick_ai_player(self, *, origin: Vec3, direction: Vec3, reach: float=MELEE_ATTACK_REACH_BLOCKS, block_hit=None) -> str | None:
        return self.ai_players.pick_actor(origin=origin, direction=direction, reach=float(reach), block_hit=block_hit)

    def attack_ai_player(self, *, origin: Vec3 | None=None, direction: Vec3 | None=None, reach: float=MELEE_ATTACK_REACH_BLOCKS) -> AiLocalAttackResult:
        attack_origin = self.player.eye_pos() if origin is None else origin
        attack_direction = self.player.view_forward() if direction is None else direction
        world_hit = self.pick_block(reach=float(reach), origin=attack_origin, direction=attack_direction)
        sprinting = attack_sprinting(attacker=self.player, walk_speed=float(self.settings.movement.walk_speed))
        return self.ai_players.player_attack_from_local(attacker=self.player, origin=attack_origin, direction=attack_direction, reach=float(reach), world_hit=world_hit, sprinting=bool(sprinting))

    def ai_route_paths(self) -> tuple[AiRoutePathSnapshot, ...]:
        return self.ai_players.route_paths()

    def ai_render_states(self):
        return self.ai_players.render_states()

    def make_camera_snapshot(self, *, enable_camera_shake: bool=True, camera_shake_strength: float=0.20) -> CameraDTO:
        eye = self.player.eye_pos()
        player = self.player
        speed = math.hypot(float(player.velocity.x), float(player.velocity.z))
        walk_speed = max(1e-6, float(self.settings.movement.walk_speed))
        speed_ratio = clampf(float(speed) / float(walk_speed), 0.0, float(PLAYER_WALK_MAX_SWING_SCALE))

        bob = 0.5 * float(speed_ratio)
        if bool(player.flying):
            bob *= 0.40
        elif not bool(player.on_ground):
            bob *= 0.75

        phase = float(self._player_motion.walk_phase_rad)
        sin_phase = math.sin(float(phase))
        cos_phase = math.cos(float(phase))
        pitch_wave = abs(math.cos(float(phase) - 0.2))
        step_eye_offset = float(player.step_eye_offset)
        camera_shake_scale = clampf(float(camera_shake_strength), 0.0, 1.0)

        cam_shake_tx = float(sin_phase * bob * 0.04) * float(camera_shake_scale)
        cam_shake_ty = float((-abs(cos_phase) * bob * 0.06) + step_eye_offset * 0.30) * float(camera_shake_scale)
        cam_shake_pitch_deg = float(pitch_wave * bob * 5.0) * float(camera_shake_scale)
        cam_shake_roll_deg = float(sin_phase * bob * 3.0) * float(camera_shake_scale)
        hurt_strength = float(player.hurt_camera_strength())
        if float(hurt_strength) > 1e-6:
            cam_shake_tx += float(player.hurt_tilt_sign) * float(hurt_strength) * 0.02 * float(camera_shake_scale)
            cam_shake_ty += float(hurt_strength) * 0.015 * float(camera_shake_scale)
            cam_shake_pitch_deg += float(hurt_strength) * 8.0 * float(camera_shake_scale)
            cam_shake_roll_deg += float(player.hurt_tilt_sign) * float(hurt_strength) * 13.0 * float(camera_shake_scale)

        if not bool(enable_camera_shake):
            cam_shake_tx = 0.0
            cam_shake_ty = 0.0
            cam_shake_pitch_deg = 0.0
            cam_shake_roll_deg = 0.0

        return CameraDTO(eye_x=eye.x, eye_y=eye.y, eye_z=eye.z, yaw_deg=self.player.yaw_deg, pitch_deg=self.player.pitch_deg, fov_deg=self.settings.fov_deg, shake_tx=float(cam_shake_tx), shake_ty=float(cam_shake_ty), shake_tz=0.0, shake_yaw_deg=0.0, shake_pitch_deg=float(cam_shake_pitch_deg), shake_roll_deg=float(cam_shake_roll_deg))

    def step(self, dt: float, move_f: float, move_s: float, jump_held: bool, jump_pressed: bool, sprint: bool, crouch: bool, mdx: float, mdy: float, creative_mode: bool, auto_jump_enabled: bool, paused_ai_actor_ids: tuple[str, ...]=()) -> SessionStepResult:
        self._sim_time_s += float(dt)
        gravity_result = self.gravity.step(self.world, float(dt), player=self.player)
        yaw_delta = (-float(mdx)) * float(self.settings.mouse_sens_deg_per_px)
        pitch_delta = float(mdy) * float(self.settings.mouse_sens_deg_per_px)

        self._update_creative_flight_toggle(creative_mode=bool(creative_mode), jump_pressed=bool(jump_pressed))

        step_result = advance_runtime_player(player=self.player, world=self.world, block_registry=self.block_registry, settings=self.settings, motion=self._player_motion, dt=float(dt), control=PlayerStepInput(move_f=float(move_f), move_s=float(move_s), jump_held=bool(jump_held), jump_pressed=bool(jump_pressed), sprint=bool(sprint), crouch=bool(crouch), yaw_delta_deg=float(yaw_delta), pitch_delta_deg=float(pitch_delta), auto_jump_enabled=bool(auto_jump_enabled)))

        fall_damage = 0.0
        void_damage = 0.0
        if not bool(creative_mode):
            fall_damage = self.player.apply_damage(fall_damage_amount(fall_distance_blocks=step_result.fall_distance_blocks), bypass_cooldown=True)
            void_damage, self._void_damage_timer_s = apply_void_damage(player=self.player, dt=float(dt), timer_s=float(self._void_damage_timer_s))
        else:
            self._void_damage_timer_s = 0.0
        ai_report = self.ai_players.step(dt=float(dt), target_player=self.player, allow_pvp=(not bool(creative_mode)), paused_actor_ids=tuple(str(actor_id) for actor_id in paused_ai_actor_ids))
        damage_taken = float(fall_damage) + float(void_damage) + float(ai_report.player_damage_taken)
        play_damage_sound = bool(float(void_damage) > 1e-6 or float(ai_report.player_damage_taken) > 1e-6)

        death_reason: str | None = None
        if not self.player.alive():
            if float(void_damage) > 1e-6:
                death_reason = "void"
            elif float(fall_damage) > 1e-6:
                death_reason = "fall"
            elif ai_report.player_death_reason is not None:
                death_reason = str(ai_report.player_death_reason)
            else:
                death_reason = "damage"
        self._death_reason = death_reason

        return SessionStepResult(jump_started=bool(step_result.jump_started), landed=bool(step_result.landed), footstep_triggered=bool(step_result.footstep_triggered), support_block_state=step_result.support_block_state, support_position=step_result.support_position, fall_distance_blocks=step_result.fall_distance_blocks, damage_taken=float(damage_taken), death_reason=death_reason, gravity_broken_blocks=tuple(gravity_result.broken_blocks), play_damage_sound=bool(play_damage_sound), ai_damage_sound_positions=tuple(ai_report.damage_sound_positions))

    def make_snapshot(self, *, enable_view_bobbing: bool=True, enable_camera_shake: bool=True, view_bobbing_strength: float=0.35, camera_shake_strength: float=0.20, is_first_person_view: bool=True) -> RenderSnapshotDTO:
        camera = self.make_camera_snapshot(enable_camera_shake=bool(enable_camera_shake), camera_shake_strength=float(camera_shake_strength))
        player_model = build_player_model_snapshot(player=self.player, motion=self._player_motion, walk_speed=float(self.settings.movement.walk_speed), is_first_person_view=bool(is_first_person_view))
        scale = 0.0 if not bool(enable_view_bobbing) else clampf(float(view_bobbing_strength), 0.0, 1.0)
        player_model = type(player_model)(base_x=float(player_model.base_x), base_y=float(player_model.base_y), base_z=float(player_model.base_z), body_yaw_deg=float(player_model.body_yaw_deg), head_yaw_deg=float(player_model.head_yaw_deg), head_pitch_deg=float(player_model.head_pitch_deg), limb_phase_rad=float(player_model.limb_phase_rad), limb_swing_amount=float(player_model.limb_swing_amount), crouch_amount=float(player_model.crouch_amount), hurt_tint_strength=float(player_model.hurt_tint_strength), first_person_tx=float(player_model.first_person_tx) * float(scale), first_person_ty=float(player_model.first_person_ty) * float(scale), first_person_tz=float(player_model.first_person_tz) * float(scale), first_person_yaw_deg=float(player_model.first_person_yaw_deg) * float(scale), first_person_pitch_deg=float(player_model.first_person_pitch_deg) * float(scale), first_person_roll_deg=float(player_model.first_person_roll_deg) * float(scale), is_first_person=bool(player_model.is_first_person))

        falling_blocks = tuple(FallingBlockRenderSampleDTO(state_str=str(sample.state_str), x=float(sample.x), y=float(sample.y), z=float(sample.z)) for sample in self.gravity.render_samples())
        return RenderSnapshotDTO(world_revision=int(self.world.revision), camera=camera, player_model=player_model, falling_blocks=falling_blocks)

    def break_block(self, reach: float=5.0, *, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.break_block(reach=float(reach), origin=origin, direction=direction)

    def pick_block(self, reach: float=5.0, *, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.pick_block(reach=float(reach), origin=origin, direction=direction)

    def interact_block_at_hit(self, hit_cell: tuple[int, int, int]):
        return self.interaction.interact_block_at_hit(hit_cell)

    def place_block_from_hit(self, hit, block_id: str | None):
        return self.interaction.place_block_from_hit(hit, block_id)

    def place_block(self, block_id: str | None, reach: float=5.0, *, crouching: bool=False, origin: Vec3 | None=None, direction: Vec3 | None=None):
        return self.interaction.place_block(block_id=block_id, reach=float(reach), crouching=bool(crouching), origin=origin, direction=direction)
