# FILE: src/maiming/application/session/session_manager.py
from __future__ import annotations

from dataclasses import dataclass, field

from maiming.core.math.vec3 import Vec3, clampf
from maiming.core.math.smoothing import exp_alpha

from maiming.domain.world.world_state import WorldState
from maiming.domain.world.world_gen import generate_test_map
from maiming.domain.entities.player_entity import PlayerEntity
from maiming.domain.systems.movement_system import MoveInput, step_bedrock
from maiming.domain.systems.collision_system import integrate_with_collisions, can_auto_jump_one_block

from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.default_registry import create_default_registry

from maiming.application.session.session_settings import SessionSettings
from maiming.application.session.render_snapshot import CameraDTO, RenderSnapshotDTO
from maiming.application.services.interaction_service import InteractionService

@dataclass
class SessionManager:
    settings: SessionSettings
    world: WorldState
    player: PlayerEntity
    block_registry: BlockRegistry

    interaction: InteractionService = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.interaction = InteractionService.create(
            world=self.world,
            player=self.player,
            block_registry=self.block_registry,
        )

    @staticmethod
    def create_default(seed: int = 0) -> "SessionManager":
        st = SessionSettings(seed=seed)
        world = generate_test_map(seed=seed)
        player = PlayerEntity(
            position=Vec3(float(st.spawn_x), float(st.spawn_y), float(st.spawn_z)),
            velocity=Vec3(0.0, 0.0, 0.0),
            yaw_deg=0.0,
            pitch_deg=0.0,
        )
        return SessionManager(
            settings=st,
            world=world,
            player=player,
            block_registry=create_default_registry(),
        )

    def respawn(self) -> None:
        p = self.player
        p.position = Vec3(
            float(self.settings.spawn_x),
            float(self.settings.spawn_y),
            float(self.settings.spawn_z),
        )
        p.velocity = Vec3(0.0, 0.0, 0.0)
        p.yaw_deg = 0.0
        p.pitch_deg = 0.0
        p.on_ground = False

        p.crouch_eye_offset = 0.0
        p.step_eye_offset = 0.0
        p.hold_jump_queued = False
        p.auto_jump_pending = False
        p.auto_jump_start_y = float(p.position.y)
        p.auto_jump_cooldown_s = 0.0

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

    def step(
        self,
        dt: float,
        move_f: float,
        move_s: float,
        jump_held: bool,
        jump_pressed: bool,
        sprint: bool,
        crouch: bool,
        mdx: float,
        mdy: float,
        auto_jump_enabled: bool,
    ) -> bool:
        prev_on_ground = bool(self.player.on_ground)
        prev_vy = float(self.player.velocity.y)

        yaw_delta = (-float(mdx)) * float(self.settings.mouse_sens_deg_per_px)
        pitch_delta = (float(mdy)) * float(self.settings.mouse_sens_deg_per_px)

        if not bool(jump_held):
            self.player.hold_jump_queued = False

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
                        from maiming.domain.systems.movement_system import _wish_dir

                        wish = _wish_dir(self.player, f, s)
                        probe = float(self.settings.movement.auto_jump_probe)
                        dx = float(wish.x) * probe
                        dz = float(wish.z) * probe

                        if can_auto_jump_one_block(
                            self.player,
                            self.world,
                            dx=dx,
                            dz=dz,
                            block_registry=self.block_registry,
                            params=self.settings.collision,
                        ):
                            jump_pulse = True
                            self.player.auto_jump_pending = True
                            self.player.auto_jump_start_y = float(self.player.position.y)

        mi = MoveInput(
            forward=clampf(move_f, -1.0, 1.0),
            strafe=clampf(move_s, -1.0, 1.0),
            sprint=bool(sprint),
            crouch=bool(crouch),
            jump_pulse=bool(jump_pulse),
            jump_held=bool(jump_held),
            yaw_delta_deg=float(yaw_delta),
            pitch_delta_deg=float(pitch_delta),
        )

        step_bedrock(self.player, mi, float(dt), params=self.settings.movement)

        report = integrate_with_collisions(
            self.player,
            self.world,
            float(dt),
            block_registry=self.block_registry,
            params=self.settings.collision,
            crouch=bool(crouch),
            jump_pressed=bool(jump_pulse),
        )

        landed_now = (not prev_on_ground) and bool(report.supported_after) and (float(prev_vy) <= 0.0)

        if bool(landed_now) and bool(jump_held):
            self.player.hold_jump_queued = True

        if bool(landed_now) and bool(self.player.auto_jump_pending):
            dy = float(self.player.position.y) - float(self.player.auto_jump_start_y)
            if dy >= float(self.settings.movement.auto_jump_success_dy):
                self.player.auto_jump_cooldown_s = float(self.settings.movement.auto_jump_cooldown_s)
            self.player.auto_jump_pending = False

        dy_corr = float(report.y_correction_dy)
        step_h = float(self.settings.collision.step_height)

        if (
            abs(dy_corr) > 1e-6
            and abs(dy_corr) <= (step_h + 1e-3)
            and bool(report.supported_before)
            and bool(report.supported_after)
            and (not bool(jump_pulse))
            and abs(float(prev_vy)) <= 1e-6
            and abs(float(self.player.velocity.y)) <= 1e-6
        ):
            self.player.step_eye_offset = float(self.player.step_eye_offset) - float(dy_corr)

        self._update_crouch_eye(float(dt), bool(crouch))
        self._update_step_eye(float(dt))
        return bool(jump_pulse)

    def make_snapshot(self) -> RenderSnapshotDTO:
        eye = self.player.eye_pos()
        cam = CameraDTO(
            eye_x=eye.x,
            eye_y=eye.y,
            eye_z=eye.z,
            yaw_deg=self.player.yaw_deg,
            pitch_deg=self.player.pitch_deg,
            fov_deg=self.settings.fov_deg,
        )
        return RenderSnapshotDTO(
            world_revision=int(self.world.revision),
            camera=cam,
        )

    def break_block(self, reach: float = 5.0) -> bool:
        return self.interaction.break_block(reach=float(reach))

    def place_block(self, block_id: str, reach: float = 5.0) -> bool:
        return self.interaction.place_block(
            block_id=str(block_id),
            reach=float(reach),
        )