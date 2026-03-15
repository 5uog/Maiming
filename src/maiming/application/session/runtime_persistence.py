# FILE: src/maiming/application/session/runtime_persistence.py
from __future__ import annotations
from pathlib import Path

from ...core.math.vec3 import Vec3
from ...domain.othello.board import OTHELLO_BOARD_SURFACE_Y, ensure_othello_board_layout, is_othello_board_footprint
from ...domain.othello.types import OthelloGameState
from ...domain.play_space import normalize_play_space_id
from ...infrastructure.persistence.app_state_store import AppState, AppStateStore, PersistedInventory, PersistedOthelloSpace, PersistedPlaySpace, PersistedPlayer, PersistedSettings, PersistedWorld
from .play_space_sessions import PlaySpaceSessions
from .runtime_preferences import RuntimePreferences, coerce_runtime_preferences
from .session_manager import SessionManager

PersistedRuntime = RuntimePreferences

def _apply_shared_settings_to_session(session: SessionManager, settings: PersistedSettings) -> None:
    session.settings.set_fov(float(settings.fov_deg))
    session.settings.set_mouse_sens(float(settings.mouse_sens_deg_per_px))
    session.settings.set_gravity(float(settings.gravity))
    session.settings.set_walk_speed(float(settings.walk_speed))
    session.settings.set_sprint_speed(float(settings.sprint_speed))
    session.settings.set_jump_v0(float(settings.jump_v0))
    session.settings.set_auto_jump_cooldown_s(float(settings.auto_jump_cooldown_s))
    session.settings.set_fly_speed(float(getattr(settings, "fly_speed", session.settings.movement.fly_speed)))
    session.settings.set_fly_ascend_speed(float(getattr(settings, "fly_ascend_speed", session.settings.movement.fly_ascend_speed)))
    session.settings.set_fly_descend_speed(float(getattr(settings, "fly_descend_speed", session.settings.movement.fly_descend_speed)))

def _load_player_into_session(*, session: SessionManager, player: PersistedPlayer, allow_flying: bool) -> None:
    runtime_player = session.player
    runtime_player.position = Vec3(float(player.pos_x), float(player.pos_y), float(player.pos_z))
    runtime_player.velocity = Vec3(float(player.vel_x), float(player.vel_y), float(player.vel_z))
    runtime_player.yaw_deg = float(player.yaw_deg)
    runtime_player.pitch_deg = float(player.pitch_deg)
    runtime_player.clamp_pitch()
    runtime_player.on_ground = bool(player.on_ground)
    runtime_player.flying = bool(getattr(player, "flying", False)) and bool(allow_flying)
    runtime_player.crouch_eye_offset = float(max(0.0, min(float(runtime_player.crouch_eye_drop), float(player.crouch_eye_offset))))
    runtime_player.hold_jump_queued = False
    runtime_player.auto_jump_pending = False
    runtime_player.auto_jump_cooldown_s = float(max(0.0, float(player.auto_jump_cooldown_s)))
    runtime_player.auto_jump_start_y = float(runtime_player.position.y)

def _maybe_replace_world(session: SessionManager, persisted_world: PersistedWorld) -> None:
    if not persisted_world.blocks and int(persisted_world.revision) <= 0:
        return
    session.world.replace_all(blocks={k: str(v) for (k, v) in persisted_world.blocks.items()}, revision=int(max(1, int(persisted_world.revision))))

def _lift_player_above_othello_board_if_needed(session: SessionManager) -> None:
    player = session.player
    if not is_othello_board_footprint(float(player.position.x), float(player.position.z)):
        return
    board_surface_y = float(OTHELLO_BOARD_SURFACE_Y)
    if float(player.position.y) >= float(board_surface_y) - 1e-6:
        return
    player.position = Vec3(float(player.position.x), float(board_surface_y), float(player.position.z))
    player.velocity = Vec3(float(player.velocity.x), max(0.0, float(player.velocity.y)), float(player.velocity.z))
    player.on_ground = False
    player.auto_jump_start_y = float(player.position.y)

def _persisted_player_from_session(session: SessionManager, *, allow_flying: bool) -> PersistedPlayer:
    player = session.player
    return PersistedPlayer(pos_x=float(player.position.x), pos_y=float(player.position.y), pos_z=float(player.position.z), vel_x=float(player.velocity.x), vel_y=float(player.velocity.y), vel_z=float(player.velocity.z), yaw_deg=float(player.yaw_deg), pitch_deg=float(player.pitch_deg), on_ground=bool(player.on_ground), flying=bool(player.flying and allow_flying), auto_jump_cooldown_s=float(max(0.0, float(player.auto_jump_cooldown_s))), crouch_eye_offset=float(max(0.0, min(float(player.crouch_eye_drop), float(player.crouch_eye_offset)))))

def _persisted_world_from_session(session: SessionManager) -> PersistedWorld:
    snapshot = session.world.snapshot_blocks()
    return PersistedWorld(revision=int(session.world.revision), blocks={k: str(v) for (k, v) in snapshot.items()})

def apply_persisted_state_if_present(*, project_root: Path, sessions: PlaySpaceSessions, renderer) -> tuple[RuntimePreferences, OthelloGameState]:
    runtime = RuntimePreferences()
    store = AppStateStore(project_root=Path(project_root))
    state = store.load()
    othello_game_state = OthelloGameState()

    if state is not None:
        persisted_settings = state.settings
        for session in sessions.all_sessions():
            _apply_shared_settings_to_session(session, persisted_settings)

        runtime = coerce_runtime_preferences(runtime=runtime, current_space_id=normalize_play_space_id(state.current_space_id), invert_x=bool(persisted_settings.invert_x), invert_y=bool(persisted_settings.invert_y), outline_selection=bool(persisted_settings.outline_selection), cloud_wire=bool(getattr(persisted_settings, "cloud_wireframe", False)), world_wire=bool(persisted_settings.world_wireframe), shadow_enabled=bool(persisted_settings.shadow_enabled), sun_az_deg=float(persisted_settings.sun_az_deg), sun_el_deg=float(persisted_settings.sun_el_deg), cloud_enabled=bool(persisted_settings.cloud_enabled), cloud_density=int(persisted_settings.cloud_density), cloud_seed=int(persisted_settings.cloud_seed), cloud_flow_direction=str(getattr(persisted_settings, "cloud_flow_direction", "west_to_east")), creative_mode=bool(getattr(persisted_settings, "creative_mode", getattr(persisted_settings, "build_mode", False))), auto_jump_enabled=bool(persisted_settings.auto_jump_enabled), auto_sprint_enabled=bool(getattr(persisted_settings, "auto_sprint_enabled", False)), hide_hud=bool(getattr(persisted_settings, "hide_hud", False)), hide_hand=bool(getattr(persisted_settings, "hide_hand", False)), fullscreen=bool(getattr(persisted_settings, "fullscreen", False)), view_bobbing_enabled=bool(getattr(persisted_settings, "view_bobbing_enabled", True)), camera_shake_enabled=bool(getattr(persisted_settings, "camera_shake_enabled", True)), view_bobbing_strength=float(getattr(persisted_settings, "view_bobbing_strength", 0.35)), camera_shake_strength=float(getattr(persisted_settings, "camera_shake_strength", 0.20)), hud_visible=bool(getattr(persisted_settings, "hud_visible", False)), render_distance_chunks=int(persisted_settings.render_distance_chunks), creative_hotbar_slots=list(state.inventory.creative_hotbar_slots), creative_selected_hotbar_index=int(state.inventory.creative_selected_hotbar_index), survival_hotbar_slots=list(state.inventory.survival_hotbar_slots), survival_selected_hotbar_index=int(state.inventory.survival_selected_hotbar_index), othello_hotbar_slots=list(state.inventory.othello_hotbar_slots), othello_selected_hotbar_index=int(state.inventory.othello_selected_hotbar_index), othello_settings=state.othello_settings)

        _load_player_into_session(session=sessions.my_world, player=state.my_world.player, allow_flying=bool(runtime.creative_mode))
        _maybe_replace_world(sessions.my_world, state.my_world.world)

        _load_player_into_session(session=sessions.othello, player=state.othello_space.player, allow_flying=False)
        _maybe_replace_world(sessions.othello, state.othello_space.world)
        ensure_othello_board_layout(sessions.othello.world)
        _lift_player_above_othello_board_if_needed(sessions.othello)
        othello_game_state = state.othello_space.othello_game_state.normalized()

    runtime.normalize()
    sessions.set_active_space(runtime.current_space_id)

    renderer.set_outline_selection_enabled(bool(runtime.outline_selection))
    renderer.set_world_wireframe(bool(runtime.world_wire))
    renderer.set_shadow_enabled(bool(runtime.shadow_enabled))
    renderer.set_sun_angles(float(runtime.sun_az_deg), float(runtime.sun_el_deg))
    renderer.set_cloud_wireframe(bool(runtime.cloud_wire))
    renderer.set_cloud_enabled(bool(runtime.cloud_enabled))
    renderer.set_cloud_density(int(runtime.cloud_density))
    renderer.set_cloud_seed(int(runtime.cloud_seed))
    renderer.set_cloud_flow_direction(str(runtime.cloud_flow_direction))
    return (runtime, othello_game_state)

def save_state(*, project_root: Path, sessions: PlaySpaceSessions, renderer, runtime: RuntimePreferences | None = None, othello_game_state: OthelloGameState | None = None, **overrides) -> None:
    _ = renderer
    state_runtime = coerce_runtime_preferences(runtime=runtime, **overrides)
    store = AppStateStore(project_root=Path(project_root))
    active_session = sessions.active_session()

    settings = PersistedSettings(fov_deg=float(active_session.settings.fov_deg), mouse_sens_deg_per_px=float(active_session.settings.mouse_sens_deg_per_px), invert_x=bool(state_runtime.invert_x), invert_y=bool(state_runtime.invert_y), outline_selection=bool(state_runtime.outline_selection), cloud_wireframe=bool(state_runtime.cloud_wire), world_wireframe=bool(state_runtime.world_wire), shadow_enabled=bool(state_runtime.shadow_enabled), sun_az_deg=float(state_runtime.sun_az_deg), sun_el_deg=float(state_runtime.sun_el_deg), cloud_enabled=bool(state_runtime.cloud_enabled), cloud_density=int(state_runtime.cloud_density), cloud_seed=int(state_runtime.cloud_seed), cloud_flow_direction=str(state_runtime.cloud_flow_direction), creative_mode=bool(state_runtime.creative_mode), auto_jump_enabled=bool(state_runtime.auto_jump_enabled), auto_sprint_enabled=bool(state_runtime.auto_sprint_enabled), hide_hud=bool(state_runtime.hide_hud), hide_hand=bool(state_runtime.hide_hand), fullscreen=bool(state_runtime.fullscreen), view_bobbing_enabled=bool(state_runtime.view_bobbing_enabled), camera_shake_enabled=bool(state_runtime.camera_shake_enabled), view_bobbing_strength=float(state_runtime.view_bobbing_strength), camera_shake_strength=float(state_runtime.camera_shake_strength), gravity=float(active_session.settings.movement.gravity), walk_speed=float(active_session.settings.movement.walk_speed), sprint_speed=float(active_session.settings.movement.sprint_speed), jump_v0=float(active_session.settings.movement.jump_v0), auto_jump_cooldown_s=float(active_session.settings.movement.auto_jump_cooldown_s), fly_speed=float(active_session.settings.movement.fly_speed), fly_ascend_speed=float(active_session.settings.movement.fly_ascend_speed), fly_descend_speed=float(active_session.settings.movement.fly_descend_speed), render_distance_chunks=int(state_runtime.render_distance_chunks), hud_visible=bool(state_runtime.hud_visible))

    inventory = PersistedInventory(creative_hotbar_slots=tuple(state_runtime.creative_hotbar_slots), creative_selected_hotbar_index=int(state_runtime.creative_selected_hotbar_index), survival_hotbar_slots=tuple(state_runtime.survival_hotbar_slots), survival_selected_hotbar_index=int(state_runtime.survival_selected_hotbar_index), othello_hotbar_slots=tuple(state_runtime.othello_hotbar_slots), othello_selected_hotbar_index=int(state_runtime.othello_selected_hotbar_index))
    persisted_othello_state = (othello_game_state or OthelloGameState()).normalized()

    state = AppState(current_space_id=normalize_play_space_id(state_runtime.current_space_id), settings=settings, inventory=inventory, othello_settings=state_runtime.othello_settings.normalized(), my_world=PersistedPlaySpace(player=_persisted_player_from_session(sessions.my_world, allow_flying=bool(state_runtime.creative_mode)), world=_persisted_world_from_session(sessions.my_world)), othello_space=PersistedOthelloSpace(player=_persisted_player_from_session(sessions.othello, allow_flying=False), world=_persisted_world_from_session(sessions.othello), othello_game_state=persisted_othello_state))
    store.save(state)