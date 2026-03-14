# FILE: src/maiming/presentation/widgets/viewport/viewport_persistence.py
from __future__ import annotations
from pathlib import Path

from ....core.math.vec3 import Vec3
from ....application.session.play_space_sessions import PlaySpaceSessions
from ....application.session.session_manager import SessionManager
from ....domain.othello.types import OthelloGameState
from ....domain.play_space import PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO, is_othello_space, normalize_play_space_id
from ....domain.world.world_gen import OTHELLO_BOARD_SURFACE_Y, ensure_othello_board_layout, is_othello_board_footprint
from ....infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from ....infrastructure.persistence.app_state_store import AppState, AppStateStore, PersistedInventory, PersistedOthelloSpace, PersistedPlaySpace, PersistedPlayer, PersistedSettings, PersistedWorld

from .viewport_runtime_state import ViewportRuntimeState

PersistedRuntime = ViewportRuntimeState

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
    p = session.player
    p.position = Vec3(float(player.pos_x), float(player.pos_y), float(player.pos_z))
    p.velocity = Vec3(float(player.vel_x), float(player.vel_y), float(player.vel_z))
    p.yaw_deg = float(player.yaw_deg)
    p.pitch_deg = float(player.pitch_deg)
    p.clamp_pitch()
    p.on_ground = bool(player.on_ground)
    p.flying = bool(getattr(player, "flying", False)) and bool(allow_flying)
    p.crouch_eye_offset = float(max(0.0, min(float(p.crouch_eye_drop), float(player.crouch_eye_offset))))
    p.hold_jump_queued = False
    p.auto_jump_pending = False
    p.auto_jump_cooldown_s = float(max(0.0, float(player.auto_jump_cooldown_s)))
    p.auto_jump_start_y = float(p.position.y)

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
    pl = session.player
    return PersistedPlayer(pos_x=float(pl.position.x), pos_y=float(pl.position.y), pos_z=float(pl.position.z), vel_x=float(pl.velocity.x), vel_y=float(pl.velocity.y), vel_z=float(pl.velocity.z), yaw_deg=float(pl.yaw_deg), pitch_deg=float(pl.pitch_deg), on_ground=bool(pl.on_ground), flying=bool(pl.flying and allow_flying), auto_jump_cooldown_s=float(max(0.0, float(pl.auto_jump_cooldown_s))), crouch_eye_offset=float(max(0.0, min(float(pl.crouch_eye_drop), float(pl.crouch_eye_offset)))))

def _persisted_world_from_session(session: SessionManager) -> PersistedWorld:
    snap = session.world.snapshot_blocks()
    return PersistedWorld(revision=int(session.world.revision), blocks={k: str(v) for (k, v) in snap.items()})

def apply_persisted_state_if_present(*, project_root: Path, sessions: PlaySpaceSessions, renderer: GLRenderer) -> tuple[ViewportRuntimeState, OthelloGameState]:
    runtime = ViewportRuntimeState()
    store = AppStateStore(project_root=Path(project_root))
    st = store.load()
    othello_game_state = OthelloGameState()

    if st is not None:
        ps = st.settings
        for session in sessions.all_sessions():
            _apply_shared_settings_to_session(session, ps)

        runtime.current_space_id = normalize_play_space_id(st.current_space_id)
        runtime.invert_x = bool(ps.invert_x)
        runtime.invert_y = bool(ps.invert_y)
        runtime.outline_selection = bool(ps.outline_selection)
        runtime.cloud_wire = bool(getattr(ps, "cloud_wireframe", False))
        runtime.world_wire = bool(ps.world_wireframe)
        runtime.shadow_enabled = bool(ps.shadow_enabled)
        runtime.sun_az_deg = float(ps.sun_az_deg)
        runtime.sun_el_deg = float(ps.sun_el_deg)
        runtime.cloud_enabled = bool(ps.cloud_enabled)
        runtime.cloud_density = int(ps.cloud_density)
        runtime.cloud_seed = int(ps.cloud_seed)
        runtime.cloud_flow_direction = str(getattr(ps, "cloud_flow_direction", "west_to_east"))
        runtime.creative_mode = bool(getattr(ps, "creative_mode", getattr(ps, "build_mode", False)))
        runtime.auto_jump_enabled = bool(ps.auto_jump_enabled)
        runtime.auto_sprint_enabled = bool(getattr(ps, "auto_sprint_enabled", False))
        runtime.hide_hud = bool(getattr(ps, "hide_hud", False))
        runtime.hide_hand = bool(getattr(ps, "hide_hand", False))
        runtime.fullscreen = bool(getattr(ps, "fullscreen", False))
        runtime.view_bobbing_enabled = bool(getattr(ps, "view_bobbing_enabled", True))
        runtime.camera_shake_enabled = bool(getattr(ps, "camera_shake_enabled", True))
        runtime.view_bobbing_strength = float(getattr(ps, "view_bobbing_strength", 0.35))
        runtime.camera_shake_strength = float(getattr(ps, "camera_shake_strength", 0.20))
        runtime.hud_visible = bool(getattr(ps, "hud_visible", False))
        runtime.render_distance_chunks = int(ps.render_distance_chunks)
        runtime.creative_hotbar_slots = list(st.inventory.creative_hotbar_slots)
        runtime.creative_selected_hotbar_index = int(st.inventory.creative_selected_hotbar_index)
        runtime.survival_hotbar_slots = list(st.inventory.survival_hotbar_slots)
        runtime.survival_selected_hotbar_index = int(st.inventory.survival_selected_hotbar_index)
        runtime.othello_hotbar_slots = list(st.inventory.othello_hotbar_slots)
        runtime.othello_selected_hotbar_index = int(st.inventory.othello_selected_hotbar_index)
        runtime.othello_settings = st.othello_settings

        _load_player_into_session(session=sessions.my_world, player=st.my_world.player, allow_flying=bool(runtime.creative_mode))
        _maybe_replace_world(sessions.my_world, st.my_world.world)

        _load_player_into_session(session=sessions.othello, player=st.othello_space.player, allow_flying=False)
        _maybe_replace_world(sessions.othello, st.othello_space.world)
        ensure_othello_board_layout(sessions.othello.world)
        _lift_player_above_othello_board_if_needed(sessions.othello)
        othello_game_state = st.othello_space.othello_game_state.normalized()

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

def _coerce_runtime(*, runtime: ViewportRuntimeState | None, current_space_id: str | None, invert_x: bool | None, invert_y: bool | None, outline_selection: bool | None, cloud_wire: bool | None, cloud_enabled: bool | None, cloud_density: int | None, cloud_seed: int | None, cloud_flow_direction: str | None, creative_mode: bool | None, auto_jump_enabled: bool | None, auto_sprint_enabled: bool | None, hide_hud: bool | None, hide_hand: bool | None, fullscreen: bool | None, view_bobbing_enabled: bool | None, camera_shake_enabled: bool | None, view_bobbing_strength: float | None, camera_shake_strength: float | None, world_wire: bool | None, shadow_enabled: bool | None, sun_az_deg: float | None, sun_el_deg: float | None, render_distance_chunks: int | None) -> ViewportRuntimeState:
    if runtime is not None:
        out = ViewportRuntimeState(current_space_id=str(runtime.current_space_id), invert_x=bool(runtime.invert_x), invert_y=bool(runtime.invert_y), outline_selection=bool(runtime.outline_selection), cloud_wire=bool(runtime.cloud_wire), cloud_enabled=bool(runtime.cloud_enabled), cloud_density=int(runtime.cloud_density), cloud_seed=int(runtime.cloud_seed), cloud_flow_direction=str(runtime.cloud_flow_direction), world_wire=bool(runtime.world_wire), shadow_enabled=bool(runtime.shadow_enabled), creative_mode=bool(runtime.creative_mode), creative_hotbar_slots=list(runtime.creative_hotbar_slots), creative_selected_hotbar_index=int(runtime.creative_selected_hotbar_index), survival_hotbar_slots=list(runtime.survival_hotbar_slots), survival_selected_hotbar_index=int(runtime.survival_selected_hotbar_index), othello_hotbar_slots=list(runtime.othello_hotbar_slots), othello_selected_hotbar_index=int(runtime.othello_selected_hotbar_index), othello_settings=runtime.othello_settings.normalized(), reach=float(runtime.reach), auto_jump_enabled=bool(runtime.auto_jump_enabled), auto_sprint_enabled=bool(runtime.auto_sprint_enabled), hide_hud=bool(runtime.hide_hud), hide_hand=bool(runtime.hide_hand), fullscreen=bool(runtime.fullscreen), view_bobbing_enabled=bool(runtime.view_bobbing_enabled), camera_shake_enabled=bool(runtime.camera_shake_enabled), view_bobbing_strength=float(runtime.view_bobbing_strength), camera_shake_strength=float(runtime.camera_shake_strength), render_distance_chunks=int(runtime.render_distance_chunks), sun_az_deg=float(runtime.sun_az_deg), sun_el_deg=float(runtime.sun_el_deg), debug_shadow=bool(runtime.debug_shadow), vsync_on=bool(runtime.vsync_on), hud_visible=bool(runtime.hud_visible))
        out.normalize()
        return out

    out = ViewportRuntimeState()

    if current_space_id is not None:
        out.current_space_id = normalize_play_space_id(current_space_id)
    if invert_x is not None:
        out.invert_x = bool(invert_x)
    if invert_y is not None:
        out.invert_y = bool(invert_y)
    if outline_selection is not None:
        out.outline_selection = bool(outline_selection)
    if cloud_wire is not None:
        out.cloud_wire = bool(cloud_wire)
    if cloud_enabled is not None:
        out.cloud_enabled = bool(cloud_enabled)
    if cloud_density is not None:
        out.cloud_density = int(cloud_density)
    if cloud_seed is not None:
        out.cloud_seed = int(cloud_seed)
    if cloud_flow_direction is not None:
        out.cloud_flow_direction = str(cloud_flow_direction)
    if creative_mode is not None:
        out.creative_mode = bool(creative_mode)
    if auto_jump_enabled is not None:
        out.auto_jump_enabled = bool(auto_jump_enabled)
    if auto_sprint_enabled is not None:
        out.auto_sprint_enabled = bool(auto_sprint_enabled)
    if hide_hud is not None:
        out.hide_hud = bool(hide_hud)
    if hide_hand is not None:
        out.hide_hand = bool(hide_hand)
    if fullscreen is not None:
        out.fullscreen = bool(fullscreen)
    if view_bobbing_enabled is not None:
        out.view_bobbing_enabled = bool(view_bobbing_enabled)
    if camera_shake_enabled is not None:
        out.camera_shake_enabled = bool(camera_shake_enabled)
    if view_bobbing_strength is not None:
        out.view_bobbing_strength = float(view_bobbing_strength)
    if camera_shake_strength is not None:
        out.camera_shake_strength = float(camera_shake_strength)
    if world_wire is not None:
        out.world_wire = bool(world_wire)
    if shadow_enabled is not None:
        out.shadow_enabled = bool(shadow_enabled)
    if sun_az_deg is not None:
        out.sun_az_deg = float(sun_az_deg)
    if sun_el_deg is not None:
        out.sun_el_deg = float(sun_el_deg)
    if render_distance_chunks is not None:
        out.render_distance_chunks = int(render_distance_chunks)

    out.normalize()
    return out

def save_state(*, project_root: Path, sessions: PlaySpaceSessions, renderer: GLRenderer, runtime: ViewportRuntimeState | None = None, othello_game_state: OthelloGameState | None = None, current_space_id: str | None = None, invert_x: bool | None = None, invert_y: bool | None = None, outline_selection: bool | None = None, cloud_wire: bool | None = None, cloud_enabled: bool | None = None, cloud_density: int | None = None, cloud_seed: int | None = None, cloud_flow_direction: str | None = None, creative_mode: bool | None = None, auto_jump_enabled: bool | None = None, auto_sprint_enabled: bool | None = None, hide_hud: bool | None = None, hide_hand: bool | None = None, fullscreen: bool | None = None, view_bobbing_enabled: bool | None = None, camera_shake_enabled: bool | None = None, view_bobbing_strength: float | None = None, camera_shake_strength: float | None = None, world_wire: bool | None = None, shadow_enabled: bool | None = None, sun_az_deg: float | None = None, sun_el_deg: float | None = None, render_distance_chunks: int | None = None) -> None:
    _ = renderer

    state_runtime = _coerce_runtime(runtime=runtime, current_space_id=current_space_id, invert_x=invert_x, invert_y=invert_y, outline_selection=outline_selection, cloud_wire=cloud_wire, cloud_enabled=cloud_enabled, cloud_density=cloud_density, cloud_seed=cloud_seed, cloud_flow_direction=cloud_flow_direction, creative_mode=creative_mode, auto_jump_enabled=auto_jump_enabled, auto_sprint_enabled=auto_sprint_enabled, hide_hud=hide_hud, hide_hand=hide_hand, fullscreen=fullscreen, view_bobbing_enabled=view_bobbing_enabled, camera_shake_enabled=camera_shake_enabled, view_bobbing_strength=view_bobbing_strength, camera_shake_strength=camera_shake_strength, world_wire=world_wire, shadow_enabled=shadow_enabled, sun_az_deg=sun_az_deg, sun_el_deg=sun_el_deg, render_distance_chunks=render_distance_chunks)

    store = AppStateStore(project_root=Path(project_root))
    active_session = sessions.active_session()

    settings = PersistedSettings(fov_deg=float(active_session.settings.fov_deg), mouse_sens_deg_per_px=float(active_session.settings.mouse_sens_deg_per_px), invert_x=bool(state_runtime.invert_x), invert_y=bool(state_runtime.invert_y), outline_selection=bool(state_runtime.outline_selection), cloud_wireframe=bool(state_runtime.cloud_wire), world_wireframe=bool(state_runtime.world_wire), shadow_enabled=bool(state_runtime.shadow_enabled), sun_az_deg=float(state_runtime.sun_az_deg), sun_el_deg=float(state_runtime.sun_el_deg), cloud_enabled=bool(state_runtime.cloud_enabled), cloud_density=int(state_runtime.cloud_density), cloud_seed=int(state_runtime.cloud_seed), cloud_flow_direction=str(state_runtime.cloud_flow_direction), creative_mode=bool(state_runtime.creative_mode), auto_jump_enabled=bool(state_runtime.auto_jump_enabled), auto_sprint_enabled=bool(state_runtime.auto_sprint_enabled), hide_hud=bool(state_runtime.hide_hud), hide_hand=bool(state_runtime.hide_hand), fullscreen=bool(state_runtime.fullscreen), view_bobbing_enabled=bool(state_runtime.view_bobbing_enabled), camera_shake_enabled=bool(state_runtime.camera_shake_enabled), view_bobbing_strength=float(state_runtime.view_bobbing_strength), camera_shake_strength=float(state_runtime.camera_shake_strength), gravity=float(active_session.settings.movement.gravity), walk_speed=float(active_session.settings.movement.walk_speed), sprint_speed=float(active_session.settings.movement.sprint_speed), jump_v0=float(active_session.settings.movement.jump_v0), auto_jump_cooldown_s=float(active_session.settings.movement.auto_jump_cooldown_s), fly_speed=float(active_session.settings.movement.fly_speed), fly_ascend_speed=float(active_session.settings.movement.fly_ascend_speed), fly_descend_speed=float(active_session.settings.movement.fly_descend_speed), render_distance_chunks=int(state_runtime.render_distance_chunks), hud_visible=bool(state_runtime.hud_visible))

    inventory = PersistedInventory(creative_hotbar_slots=tuple(state_runtime.creative_hotbar_slots), creative_selected_hotbar_index=int(state_runtime.creative_selected_hotbar_index), survival_hotbar_slots=tuple(state_runtime.survival_hotbar_slots), survival_selected_hotbar_index=int(state_runtime.survival_selected_hotbar_index), othello_hotbar_slots=tuple(state_runtime.othello_hotbar_slots), othello_selected_hotbar_index=int(state_runtime.othello_selected_hotbar_index))

    persisted_othello_state = (othello_game_state or OthelloGameState()).normalized()

    state = AppState(current_space_id=normalize_play_space_id(state_runtime.current_space_id), settings=settings, inventory=inventory, othello_settings=state_runtime.othello_settings.normalized(), my_world=PersistedPlaySpace(player=_persisted_player_from_session(sessions.my_world, allow_flying=bool(state_runtime.creative_mode)), world=_persisted_world_from_session(sessions.my_world)), othello_space=PersistedOthelloSpace(player=_persisted_player_from_session(sessions.othello, allow_flying=False), world=_persisted_world_from_session(sessions.othello), othello_game_state=persisted_othello_state))
    store.save(state)