# FILE: src/maiming/presentation/widgets/viewport/viewport_persistence.py
from __future__ import annotations
from pathlib import Path

from ....core.math.vec3 import Vec3
from ....application.session.session_manager import SessionManager
from ....infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from ....infrastructure.persistence.app_state_store import AppState, AppStateStore, PersistedInventory, PersistedPlayer, PersistedSettings, PersistedWorld

from .viewport_runtime_state import ViewportRuntimeState

PersistedRuntime = ViewportRuntimeState

def apply_persisted_state_if_present(*, project_root: Path, session: SessionManager, renderer: GLRenderer) -> ViewportRuntimeState:
    runtime = ViewportRuntimeState()
    store = AppStateStore(project_root=Path(project_root))
    st = store.load()

    if st is not None:
        ps = st.settings
        session.settings.set_fov(float(ps.fov_deg))
        session.settings.set_mouse_sens(float(ps.mouse_sens_deg_per_px))
        session.settings.set_gravity(float(ps.gravity))
        session.settings.set_walk_speed(float(ps.walk_speed))
        session.settings.set_sprint_speed(float(ps.sprint_speed))
        session.settings.set_jump_v0(float(ps.jump_v0))
        session.settings.set_auto_jump_cooldown_s(float(ps.auto_jump_cooldown_s))
        session.settings.set_fly_speed(float(getattr(ps, "fly_speed", session.settings.movement.fly_speed)))
        session.settings.set_fly_ascend_speed(float(getattr(ps, "fly_ascend_speed", session.settings.movement.fly_ascend_speed)))
        session.settings.set_fly_descend_speed(float(getattr(ps, "fly_descend_speed", session.settings.movement.fly_descend_speed)))

        runtime.invert_x = bool(ps.invert_x)
        runtime.invert_y = bool(ps.invert_y)
        runtime.outline_selection = bool(ps.outline_selection)
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
        runtime.render_distance_chunks = int(ps.render_distance_chunks)
        runtime.creative_hotbar_slots = list(st.inventory.creative_hotbar_slots)
        runtime.creative_selected_hotbar_index = int(st.inventory.creative_selected_hotbar_index)
        runtime.survival_hotbar_slots = list(st.inventory.survival_hotbar_slots)
        runtime.survival_selected_hotbar_index = int(st.inventory.survival_selected_hotbar_index)

        pp = st.player
        p = session.player
        p.position = Vec3(float(pp.pos_x), float(pp.pos_y), float(pp.pos_z))
        p.velocity = Vec3(float(pp.vel_x), float(pp.vel_y), float(pp.vel_z))
        p.yaw_deg = float(pp.yaw_deg)
        p.pitch_deg = float(pp.pitch_deg)
        p.clamp_pitch()
        p.on_ground = bool(pp.on_ground)
        p.flying = bool(getattr(pp, "flying", False)) and bool(runtime.creative_mode)
        p.crouch_eye_offset = float(max(0.0, min(float(p.crouch_eye_drop), float(pp.crouch_eye_offset))))
        p.hold_jump_queued = False
        p.auto_jump_pending = False
        p.auto_jump_cooldown_s = float(max(0.0, float(pp.auto_jump_cooldown_s)))
        p.auto_jump_start_y = float(p.position.y)

        pw = st.world
        if pw.blocks:
            session.world.replace_all(blocks={k: str(v) for (k, v) in pw.blocks.items()}, revision=int(max(1, int(pw.revision))))

    runtime.normalize()
    runtime.hud_visible = False
    renderer.set_outline_selection_enabled(bool(runtime.outline_selection))
    renderer.set_world_wireframe(bool(runtime.world_wire))
    renderer.set_shadow_enabled(bool(runtime.shadow_enabled))
    renderer.set_sun_angles(float(runtime.sun_az_deg), float(runtime.sun_el_deg))
    renderer.set_cloud_wireframe(bool(runtime.cloud_wire))
    renderer.set_cloud_enabled(bool(runtime.cloud_enabled))
    renderer.set_cloud_density(int(runtime.cloud_density))
    renderer.set_cloud_seed(int(runtime.cloud_seed))
    renderer.set_cloud_flow_direction(str(runtime.cloud_flow_direction))

    return runtime

def _coerce_runtime(*, runtime: ViewportRuntimeState | None, invert_x: bool | None, invert_y: bool | None, outline_selection: bool | None, cloud_enabled: bool | None, cloud_density: int | None, cloud_seed: int | None, cloud_flow_direction: str | None, creative_mode: bool | None, auto_jump_enabled: bool | None, auto_sprint_enabled: bool | None, world_wire: bool | None, shadow_enabled: bool | None, sun_az_deg: float | None, sun_el_deg: float | None, render_distance_chunks: int | None) -> ViewportRuntimeState:
    if runtime is not None:
        out = ViewportRuntimeState(invert_x=bool(runtime.invert_x), invert_y=bool(runtime.invert_y), outline_selection=bool(runtime.outline_selection), cloud_wire=bool(runtime.cloud_wire), cloud_enabled=bool(runtime.cloud_enabled), cloud_density=int(runtime.cloud_density), cloud_seed=int(runtime.cloud_seed), cloud_flow_direction=str(runtime.cloud_flow_direction), world_wire=bool(runtime.world_wire), shadow_enabled=bool(runtime.shadow_enabled), creative_mode=bool(runtime.creative_mode), creative_hotbar_slots=list(runtime.creative_hotbar_slots), creative_selected_hotbar_index=int(runtime.creative_selected_hotbar_index), survival_hotbar_slots=list(runtime.survival_hotbar_slots), survival_selected_hotbar_index=int(runtime.survival_selected_hotbar_index), reach=float(runtime.reach), auto_jump_enabled=bool(runtime.auto_jump_enabled), auto_sprint_enabled=bool(runtime.auto_sprint_enabled), render_distance_chunks=int(runtime.render_distance_chunks), sun_az_deg=float(runtime.sun_az_deg), sun_el_deg=float(runtime.sun_el_deg), debug_shadow=bool(runtime.debug_shadow), vsync_on=bool(runtime.vsync_on), hud_visible=bool(runtime.hud_visible))
        out.normalize()
        return out

    out = ViewportRuntimeState()

    if invert_x is not None:
        out.invert_x = bool(invert_x)
    if invert_y is not None:
        out.invert_y = bool(invert_y)
    if outline_selection is not None:
        out.outline_selection = bool(outline_selection)

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

def save_state(*, project_root: Path, session: SessionManager, renderer: GLRenderer, runtime: ViewportRuntimeState | None = None, invert_x: bool | None = None, invert_y: bool | None = None, outline_selection: bool | None = None, cloud_enabled: bool | None = None, cloud_density: int | None = None, cloud_seed: int | None = None, cloud_flow_direction: str | None = None, creative_mode: bool | None = None, auto_jump_enabled: bool | None = None, auto_sprint_enabled: bool | None = None, world_wire: bool | None = None, shadow_enabled: bool | None = None, sun_az_deg: float | None = None, sun_el_deg: float | None = None, render_distance_chunks: int | None = None) -> None:
    _ = renderer

    state_runtime = _coerce_runtime(runtime=runtime, invert_x=invert_x, invert_y=invert_y, outline_selection=outline_selection, cloud_enabled=cloud_enabled, cloud_density=cloud_density, cloud_seed=cloud_seed, cloud_flow_direction=cloud_flow_direction, creative_mode=creative_mode, auto_jump_enabled=auto_jump_enabled, auto_sprint_enabled=auto_sprint_enabled, world_wire=world_wire, shadow_enabled=shadow_enabled, sun_az_deg=sun_az_deg, sun_el_deg=sun_el_deg, render_distance_chunks=render_distance_chunks)

    store = AppStateStore(project_root=Path(project_root))

    settings = PersistedSettings(fov_deg=float(session.settings.fov_deg), mouse_sens_deg_per_px=float(session.settings.mouse_sens_deg_per_px), invert_x=bool(state_runtime.invert_x), invert_y=bool(state_runtime.invert_y), outline_selection=bool(state_runtime.outline_selection), world_wireframe=bool(state_runtime.world_wire), shadow_enabled=bool(state_runtime.shadow_enabled), sun_az_deg=float(state_runtime.sun_az_deg), sun_el_deg=float(state_runtime.sun_el_deg), cloud_enabled=bool(state_runtime.cloud_enabled), cloud_density=int(state_runtime.cloud_density), cloud_seed=int(state_runtime.cloud_seed), cloud_flow_direction=str(state_runtime.cloud_flow_direction), creative_mode=bool(state_runtime.creative_mode), auto_jump_enabled=bool(state_runtime.auto_jump_enabled), auto_sprint_enabled=bool(state_runtime.auto_sprint_enabled), gravity=float(session.settings.movement.gravity), walk_speed=float(session.settings.movement.walk_speed), sprint_speed=float(session.settings.movement.sprint_speed), jump_v0=float(session.settings.movement.jump_v0), auto_jump_cooldown_s=float(session.settings.movement.auto_jump_cooldown_s), fly_speed=float(session.settings.movement.fly_speed), fly_ascend_speed=float(session.settings.movement.fly_ascend_speed), fly_descend_speed=float(session.settings.movement.fly_descend_speed), render_distance_chunks=int(state_runtime.render_distance_chunks), hud_visible=bool(state_runtime.hud_visible))

    inventory = PersistedInventory(creative_hotbar_slots=tuple(state_runtime.creative_hotbar_slots), creative_selected_hotbar_index=int(state_runtime.creative_selected_hotbar_index), survival_hotbar_slots=tuple(state_runtime.survival_hotbar_slots), survival_selected_hotbar_index=int(state_runtime.survival_selected_hotbar_index))

    pl = session.player
    player = PersistedPlayer(pos_x=float(pl.position.x), pos_y=float(pl.position.y), pos_z=float(pl.position.z), vel_x=float(pl.velocity.x), vel_y=float(pl.velocity.y), vel_z=float(pl.velocity.z), yaw_deg=float(pl.yaw_deg), pitch_deg=float(pl.pitch_deg), on_ground=bool(pl.on_ground), flying=bool(pl.flying and state_runtime.creative_mode), auto_jump_cooldown_s=float(max(0.0, float(pl.auto_jump_cooldown_s))), crouch_eye_offset=float(max(0.0, min(float(pl.crouch_eye_drop), float(pl.crouch_eye_offset)))))

    snap = session.world.snapshot_blocks()
    world = PersistedWorld(revision=int(session.world.revision), blocks={k: str(v) for (k, v) in snap.items()})

    state = AppState(settings=settings, inventory=inventory, player=player, world=world)
    store.save(state)