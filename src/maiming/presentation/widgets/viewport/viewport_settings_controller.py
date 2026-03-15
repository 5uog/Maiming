# FILE: src/maiming/presentation/widgets/viewport/viewport_settings_controller.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .view_model_visibility import view_model_visible

if TYPE_CHECKING:
    from .gl_viewport_widget import GLViewportWidget

def bind_settings_overlay(viewport: "GLViewportWidget") -> None:
    overlay = viewport._settings
    overlay.back_requested.connect(viewport._back_from_settings)
    overlay.fov_changed.connect(viewport._set_fov)
    overlay.sens_changed.connect(viewport._set_sens)
    overlay.invert_x_changed.connect(viewport._set_invert_x)
    overlay.invert_y_changed.connect(viewport._set_invert_y)
    overlay.fullscreen_changed.connect(viewport._set_fullscreen)
    overlay.hide_hud_changed.connect(viewport._set_hide_hud)
    overlay.hide_hand_changed.connect(viewport._set_hide_hand)
    overlay.view_bobbing_changed.connect(viewport._set_view_bobbing_enabled)
    overlay.camera_shake_changed.connect(viewport._set_camera_shake_enabled)
    overlay.view_bobbing_strength_changed.connect(viewport._set_view_bobbing_strength)
    overlay.camera_shake_strength_changed.connect(viewport._set_camera_shake_strength)
    overlay.outline_selection_changed.connect(viewport._set_outline_selection)
    overlay.cloud_wireframe_changed.connect(viewport._set_cloud_wire)
    overlay.clouds_enabled_changed.connect(viewport._set_cloud_enabled)
    overlay.cloud_density_changed.connect(viewport._set_cloud_density)
    overlay.cloud_seed_changed.connect(viewport._set_cloud_seed)
    overlay.cloud_flow_direction_changed.connect(viewport._set_cloud_flow_direction)
    overlay.world_wireframe_changed.connect(viewport._set_world_wire)
    overlay.shadow_enabled_changed.connect(viewport._set_shadow_enabled)
    overlay.sun_azimuth_changed.connect(viewport._set_sun_azimuth)
    overlay.sun_elevation_changed.connect(viewport._set_sun_elevation)
    overlay.creative_mode_changed.connect(viewport._set_creative_mode)
    overlay.auto_jump_changed.connect(viewport._set_auto_jump)
    overlay.auto_sprint_changed.connect(viewport._set_auto_sprint)
    overlay.gravity_changed.connect(viewport._set_gravity)
    overlay.walk_speed_changed.connect(viewport._set_walk_speed)
    overlay.sprint_speed_changed.connect(viewport._set_sprint_speed)
    overlay.jump_v0_changed.connect(viewport._set_jump_v0)
    overlay.auto_jump_cooldown_changed.connect(viewport._set_auto_jump_cooldown_s)
    overlay.fly_speed_changed.connect(viewport._set_fly_speed)
    overlay.fly_ascend_speed_changed.connect(viewport._set_fly_ascend_speed)
    overlay.fly_descend_speed_changed.connect(viewport._set_fly_descend_speed)
    overlay.advanced_reset_requested.connect(viewport._reset_advanced_defaults)
    overlay.render_distance_changed.connect(viewport._set_render_distance)

def sync_state_from_renderer_sun(viewport: "GLViewportWidget") -> None:
    azimuth_deg, elevation_deg = viewport._renderer.sun_angles()
    viewport._state.sun_az_deg = float(azimuth_deg)
    viewport._state.sun_el_deg = float(elevation_deg)
    viewport._state.normalize()

def apply_runtime_to_renderer(viewport: "GLViewportWidget") -> None:
    viewport._state.normalize()
    viewport._renderer.set_debug_shadow(bool(viewport._state.debug_shadow))
    viewport._renderer.set_outline_selection_enabled(bool(viewport._state.outline_selection))
    viewport._renderer.set_cloud_wireframe(bool(viewport._state.cloud_wire))
    viewport._renderer.set_cloud_enabled(bool(viewport._state.cloud_enabled))
    viewport._renderer.set_cloud_density(int(viewport._state.cloud_density))
    viewport._renderer.set_cloud_seed(int(viewport._state.cloud_seed))
    viewport._renderer.set_cloud_flow_direction(str(viewport._state.cloud_flow_direction))
    viewport._renderer.set_shadow_enabled(bool(viewport._state.shadow_enabled))
    viewport._renderer.set_world_wireframe(bool(viewport._state.world_wire))
    viewport._renderer.set_sun_angles(float(viewport._state.sun_az_deg), float(viewport._state.sun_el_deg))

def sync_cloud_motion_pause(viewport: "GLViewportWidget") -> None:
    viewport._renderer.set_cloud_motion_paused(bool(viewport._overlays.paused()))

def inventory_available(viewport: "GLViewportWidget") -> bool:
    return not viewport._state.is_othello_space()

def sync_hotbar_widgets(viewport: "GLViewportWidget") -> None:
    viewport._state.normalize()
    slots = viewport._state.hotbar_snapshot()
    selected_index = viewport._state.othello_selected_hotbar_index if viewport._state.is_othello_space() else (viewport._state.creative_selected_hotbar_index if bool(viewport._state.creative_mode) else viewport._state.survival_selected_hotbar_index)
    viewport._inventory.set_creative_mode(bool(viewport._state.creative_mode and inventory_available(viewport)))
    viewport._inventory.sync_hotbar(slots=slots, selected_index=int(selected_index))
    viewport._hotbar.sync_hotbar(slots=slots, selected_index=int(selected_index))

def current_item_id(viewport: "GLViewportWidget") -> str | None:
    viewport._state.normalize()
    return viewport._state.current_item_id()

def current_block_id(viewport: "GLViewportWidget") -> str | None:
    viewport._state.normalize()
    return viewport._state.current_block_id()

def sync_view_model_visibility(viewport: "GLViewportWidget") -> None:
    visible = view_model_visible(hide_hand=bool(viewport._state.hide_hand))
    viewport._first_person_motion.set_view_model_visible(bool(visible))

def sync_first_person_target(viewport: "GLViewportWidget") -> None:
    viewport._first_person_motion.set_target_block_id(current_block_id(viewport))
    sync_view_model_visibility(viewport)

def select_hotbar_slot(viewport: "GLViewportWidget", slot_index: int) -> None:
    viewport._state.select_hotbar_index(int(slot_index))
    sync_hotbar_widgets(viewport)
    sync_first_person_target(viewport)

def assign_hotbar_slot(viewport: "GLViewportWidget", slot_index: int, item_id: str) -> None:
    viewport._state.set_hotbar_slot(int(slot_index), str(item_id))
    sync_hotbar_widgets(viewport)
    sync_first_person_target(viewport)

def cycle_hotbar(viewport: "GLViewportWidget", step: int) -> None:
    viewport._state.cycle_hotbar(int(step))
    sync_hotbar_widgets(viewport)
    sync_first_person_target(viewport)

def sync_settings_values(viewport: "GLViewportWidget") -> None:
    sync_state_from_renderer_sun(viewport)
    viewport._settings.sync_values(fov_deg=viewport._session.settings.fov_deg, sens_deg_per_px=viewport._session.settings.mouse_sens_deg_per_px, inv_x=viewport._state.invert_x, inv_y=viewport._state.invert_y, fullscreen=viewport._state.fullscreen, hide_hud=viewport._state.hide_hud, hide_hand=viewport._state.hide_hand, view_bobbing_enabled=viewport._state.view_bobbing_enabled, camera_shake_enabled=viewport._state.camera_shake_enabled, view_bobbing_strength=float(viewport._state.view_bobbing_strength), camera_shake_strength=float(viewport._state.camera_shake_strength), outline_selection=viewport._state.outline_selection, cloud_wire=viewport._state.cloud_wire, clouds_enabled=viewport._state.cloud_enabled, cloud_density=int(viewport._state.cloud_density), cloud_seed=int(viewport._state.cloud_seed), cloud_flow_direction=str(viewport._state.cloud_flow_direction), world_wire=viewport._state.world_wire, shadow_enabled=viewport._state.shadow_enabled, sun_az_deg=viewport._state.sun_az_deg, sun_el_deg=viewport._state.sun_el_deg, creative_mode=viewport._state.creative_mode, auto_jump_enabled=viewport._state.auto_jump_enabled, auto_sprint_enabled=viewport._state.auto_sprint_enabled, gravity=float(viewport._session.settings.movement.gravity), walk_speed=float(viewport._session.settings.movement.walk_speed), sprint_speed=float(viewport._session.settings.movement.sprint_speed), jump_v0=float(viewport._session.settings.movement.jump_v0), auto_jump_cooldown_s=float(viewport._session.settings.movement.auto_jump_cooldown_s), fly_speed=float(viewport._session.settings.movement.fly_speed), fly_ascend_speed=float(viewport._session.settings.movement.fly_ascend_speed), fly_descend_speed=float(viewport._session.settings.movement.fly_descend_speed), render_distance_chunks=int(viewport._state.render_distance_chunks))

def set_fov(viewport: "GLViewportWidget", fov: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_fov(float(fov)))

def set_sens(viewport: "GLViewportWidget", sens: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_mouse_sens(float(sens)))

def set_invert_x(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.invert_x = bool(on)

def set_invert_y(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.invert_y = bool(on)

def set_fullscreen(viewport: "GLViewportWidget", on: bool) -> None:
    enabled = bool(on)
    if enabled == bool(viewport._state.fullscreen):
        return
    viewport._state.fullscreen = enabled
    viewport.fullscreen_changed.emit(bool(viewport._state.fullscreen))

def set_hide_hud(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.hide_hud = bool(on)
    viewport._sync_gameplay_hud_visibility()

def set_hide_hand(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.hide_hand = bool(on)
    sync_view_model_visibility(viewport)

def set_view_bobbing_enabled(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.view_bobbing_enabled = bool(on)

def set_camera_shake_enabled(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.camera_shake_enabled = bool(on)

def set_view_bobbing_strength(viewport: "GLViewportWidget", strength: float) -> None:
    viewport._state.view_bobbing_strength = float(strength)
    viewport._state.normalize()

def set_camera_shake_strength(viewport: "GLViewportWidget", strength: float) -> None:
    viewport._state.camera_shake_strength = float(strength)
    viewport._state.normalize()

def set_outline_selection(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.outline_selection = bool(on)
    viewport._renderer.set_outline_selection_enabled(bool(viewport._state.outline_selection))

def set_cloud_wire(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.cloud_wire = bool(on)
    viewport._renderer.set_cloud_wireframe(bool(viewport._state.cloud_wire))

def set_cloud_enabled(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.cloud_enabled = bool(on)
    viewport._renderer.set_cloud_enabled(bool(viewport._state.cloud_enabled))

def set_cloud_density(viewport: "GLViewportWidget", density: int) -> None:
    viewport._state.cloud_density = int(density)
    viewport._state.normalize()
    viewport._renderer.set_cloud_density(int(viewport._state.cloud_density))

def set_cloud_seed(viewport: "GLViewportWidget", seed: int) -> None:
    viewport._state.cloud_seed = int(seed)
    viewport._state.normalize()
    viewport._renderer.set_cloud_seed(int(viewport._state.cloud_seed))

def set_cloud_flow_direction(viewport: "GLViewportWidget", direction: str) -> None:
    viewport._state.cloud_flow_direction = str(direction)
    viewport._state.normalize()
    viewport._renderer.set_cloud_flow_direction(str(viewport._state.cloud_flow_direction))

def set_world_wire(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.world_wire = bool(on)
    viewport._renderer.set_world_wireframe(bool(viewport._state.world_wire))

def set_shadow_enabled(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.shadow_enabled = bool(on)
    viewport._renderer.set_shadow_enabled(bool(viewport._state.shadow_enabled))

def set_sun_azimuth(viewport: "GLViewportWidget", azimuth_deg: float) -> None:
    viewport._state.sun_az_deg = float(azimuth_deg)
    viewport._state.normalize()
    viewport._renderer.set_sun_angles(float(viewport._state.sun_az_deg), float(viewport._state.sun_el_deg))

def set_sun_elevation(viewport: "GLViewportWidget", elevation_deg: float) -> None:
    viewport._state.sun_el_deg = float(elevation_deg)
    viewport._state.normalize()
    viewport._renderer.set_sun_angles(float(viewport._state.sun_az_deg), float(viewport._state.sun_el_deg))

def set_creative_mode(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.creative_mode = bool(on)
    if not bool(viewport._state.creative_mode):
        viewport._for_each_session(lambda session: setattr(session.player, "flying", False))
    sync_hotbar_widgets(viewport)
    sync_first_person_target(viewport)

def set_auto_jump(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.auto_jump_enabled = bool(on)

def set_auto_sprint(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.auto_sprint_enabled = bool(on)

def set_gravity(viewport: "GLViewportWidget", gravity: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_gravity(float(gravity)))

def set_walk_speed(viewport: "GLViewportWidget", walk_speed: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_walk_speed(float(walk_speed)))

def set_sprint_speed(viewport: "GLViewportWidget", sprint_speed: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_sprint_speed(float(sprint_speed)))

def set_jump_v0(viewport: "GLViewportWidget", jump_v0: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_jump_v0(float(jump_v0)))

def set_auto_jump_cooldown_s(viewport: "GLViewportWidget", cooldown_s: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_auto_jump_cooldown_s(float(cooldown_s)))

def set_fly_speed(viewport: "GLViewportWidget", fly_speed: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_fly_speed(float(fly_speed)))

def set_fly_ascend_speed(viewport: "GLViewportWidget", fly_ascend_speed: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_fly_ascend_speed(float(fly_ascend_speed)))

def set_fly_descend_speed(viewport: "GLViewportWidget", fly_descend_speed: float) -> None:
    viewport._for_each_session(lambda session: session.settings.set_fly_descend_speed(float(fly_descend_speed)))

def reset_advanced_defaults(viewport: "GLViewportWidget") -> None:
    viewport._for_each_session(lambda session: session.settings.reset_advanced_movement_defaults())
    sync_settings_values(viewport)

def set_render_distance(viewport: "GLViewportWidget", render_distance_chunks: int) -> None:
    viewport._state.render_distance_chunks = int(render_distance_chunks)
    viewport._state.normalize()