# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from typing import TYPE_CHECKING

from .....application.context.runtime.audio_preferences import AudioPreferences
from .....application.handlers.keybinds import KeybindSettings
from .....application.pipelines.runtime_state_pipeline import apply_runtime_to_renderer as apply_runtime_to_renderer_state
from .....application.pipelines.runtime_state_pipeline import sync_runtime_sun_from_renderer

if TYPE_CHECKING:
    from ..gl_viewport_widget import GLViewportWidget

def bind_settings_overlay(viewport: "GLViewportWidget") -> None:
    from . import interaction_controller

    overlay = viewport._settings
    overlay.back_requested.connect(lambda: interaction_controller.back_from_settings(viewport))
    overlay.fov_changed.connect(lambda value: set_fov(viewport, float(value)))
    overlay.sens_changed.connect(lambda value: set_sens(viewport, float(value)))
    overlay.invert_x_changed.connect(lambda on: set_invert_x(viewport, bool(on)))
    overlay.invert_y_changed.connect(lambda on: set_invert_y(viewport, bool(on)))
    overlay.fullscreen_changed.connect(lambda on: set_fullscreen(viewport, bool(on)))
    overlay.hide_hud_changed.connect(lambda on: set_hide_hud(viewport, bool(on)))
    overlay.hide_hand_changed.connect(lambda on: set_hide_hand(viewport, bool(on)))
    overlay.view_bobbing_changed.connect(lambda on: set_view_bobbing_enabled(viewport, bool(on)))
    overlay.camera_shake_changed.connect(lambda on: set_camera_shake_enabled(viewport, bool(on)))
    overlay.view_bobbing_strength_changed.connect(lambda value: set_view_bobbing_strength(viewport, float(value)))
    overlay.camera_shake_strength_changed.connect(lambda value: set_camera_shake_strength(viewport, float(value)))
    overlay.animated_textures_changed.connect(lambda on: set_animated_textures_enabled(viewport, bool(on)))
    overlay.outline_selection_changed.connect(lambda on: set_outline_selection(viewport, bool(on)))
    overlay.cloud_wireframe_changed.connect(lambda on: set_cloud_wire(viewport, bool(on)))
    overlay.clouds_enabled_changed.connect(lambda on: set_cloud_enabled(viewport, bool(on)))
    overlay.cloud_density_changed.connect(lambda value: set_cloud_density(viewport, int(value)))
    overlay.cloud_seed_changed.connect(lambda value: set_cloud_seed(viewport, int(value)))
    overlay.cloud_flow_direction_changed.connect(lambda direction: set_cloud_flow_direction(viewport, str(direction)))
    overlay.world_wireframe_changed.connect(lambda on: set_world_wire(viewport, bool(on)))
    overlay.shadow_enabled_changed.connect(lambda on: set_shadow_enabled(viewport, bool(on)))
    overlay.sun_azimuth_changed.connect(lambda value: set_sun_azimuth(viewport, float(value)))
    overlay.sun_elevation_changed.connect(lambda value: set_sun_elevation(viewport, float(value)))
    overlay.creative_mode_changed.connect(lambda on: set_creative_mode(viewport, bool(on)))
    overlay.auto_jump_changed.connect(lambda on: set_auto_jump(viewport, bool(on)))
    overlay.auto_sprint_changed.connect(lambda on: set_auto_sprint(viewport, bool(on)))
    overlay.gravity_changed.connect(lambda value: set_gravity(viewport, float(value)))
    overlay.walk_speed_changed.connect(lambda value: set_walk_speed(viewport, float(value)))
    overlay.sprint_speed_changed.connect(lambda value: set_sprint_speed(viewport, float(value)))
    overlay.jump_v0_changed.connect(lambda value: set_jump_v0(viewport, float(value)))
    overlay.auto_jump_cooldown_changed.connect(lambda value: set_auto_jump_cooldown_s(viewport, float(value)))
    overlay.fly_speed_changed.connect(lambda value: set_fly_speed(viewport, float(value)))
    overlay.fly_ascend_speed_changed.connect(lambda value: set_fly_ascend_speed(viewport, float(value)))
    overlay.fly_descend_speed_changed.connect(lambda value: set_fly_descend_speed(viewport, float(value)))
    overlay.advanced_reset_requested.connect(lambda: reset_advanced_defaults(viewport))
    overlay.render_distance_changed.connect(lambda value: set_render_distance(viewport, int(value)))
    overlay.keybind_changed.connect(lambda action, binding: set_keybind(viewport, str(action), str(binding)))
    overlay.keybind_reset_requested.connect(lambda: reset_keybinds(viewport))
    overlay.master_volume_changed.connect(lambda value: set_master_volume(viewport, float(value)))
    overlay.ambient_volume_changed.connect(lambda value: set_ambient_volume(viewport, float(value)))
    overlay.block_volume_changed.connect(lambda value: set_block_volume(viewport, float(value)))
    overlay.player_volume_changed.connect(lambda value: set_player_volume(viewport, float(value)))

def sync_state_from_renderer_sun(viewport: "GLViewportWidget") -> None:
    sync_runtime_sun_from_renderer(viewport._state, viewport._renderer)

def apply_runtime_to_renderer(viewport: "GLViewportWidget") -> None:
    apply_runtime_to_renderer_state(viewport._state, viewport._renderer)

def sync_cloud_motion_pause(viewport: "GLViewportWidget") -> None:
    viewport._renderer.set_cloud_motion_paused(bool(viewport._overlays.paused()))

def sync_input_bindings(viewport: "GLViewportWidget") -> None:
    viewport._adapter.set_keybinds(viewport._state.keybinds.normalized())

def sync_audio_preferences(viewport: "GLViewportWidget") -> None:
    if hasattr(viewport, "_audio") and viewport._audio is not None:
        viewport._audio.set_preferences(viewport._state.audio.normalized())

def inventory_available(viewport: "GLViewportWidget") -> bool:
    return not viewport._state.is_othello_space()

def sync_hotbar_widgets(viewport: "GLViewportWidget") -> None:
    viewport._state.normalize()
    slots = viewport._state.hotbar_snapshot()
    selected_index = viewport._state.active_hotbar_index()

    viewport._inventory.set_creative_mode(bool(viewport._state.creative_mode and inventory_available(viewport)))
    viewport._inventory.set_keybinds(viewport._state.keybinds)
    viewport._inventory.set_animations_enabled(bool(viewport._state.animated_textures_enabled))
    viewport._hotbar.set_animations_enabled(bool(viewport._state.animated_textures_enabled))
    viewport._inventory.sync_hotbar(slots=slots, selected_index=int(selected_index))
    viewport._hotbar.sync_hotbar(slots=slots, selected_index=int(selected_index))

def current_item_id(viewport: "GLViewportWidget") -> str | None:
    viewport._state.normalize()
    return viewport._state.current_item_id()

def current_block_id(viewport: "GLViewportWidget") -> str | None:
    viewport._state.normalize()
    return viewport._state.current_block_id()

def sync_view_model_visibility(viewport: "GLViewportWidget") -> None:
    viewport._first_person_motion.set_view_model_visible(bool(viewport._state.view_model_visible()))

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

def clear_selected_hotbar_slot(viewport: "GLViewportWidget") -> None:
    viewport._state.clear_selected_hotbar_slot()
    sync_hotbar_widgets(viewport)
    sync_first_person_target(viewport)

def sync_settings_values(viewport: "GLViewportWidget") -> None:
    sync_state_from_renderer_sun(viewport)
    viewport._settings.sync_values(fov_deg=viewport._session.settings.fov_deg, sens_deg_per_px=viewport._session.settings.mouse_sens_deg_per_px, inv_x=viewport._state.invert_x, inv_y=viewport._state.invert_y, fullscreen=viewport._state.fullscreen, hide_hud=viewport._state.hide_hud, hide_hand=viewport._state.hide_hand, view_bobbing_enabled=viewport._state.view_bobbing_enabled, camera_shake_enabled=viewport._state.camera_shake_enabled, view_bobbing_strength=float(viewport._state.view_bobbing_strength), camera_shake_strength=float(viewport._state.camera_shake_strength), animated_textures_enabled=bool(viewport._state.animated_textures_enabled), outline_selection=viewport._state.outline_selection, cloud_wire=viewport._state.cloud_wire, clouds_enabled=viewport._state.cloud_enabled, cloud_density=int(viewport._state.cloud_density), cloud_seed=int(viewport._state.cloud_seed), cloud_flow_direction=str(viewport._state.cloud_flow_direction), world_wire=viewport._state.world_wire, shadow_enabled=viewport._state.shadow_enabled, sun_az_deg=viewport._state.sun_az_deg, sun_el_deg=viewport._state.sun_el_deg, creative_mode=viewport._state.creative_mode, auto_jump_enabled=viewport._state.auto_jump_enabled, auto_sprint_enabled=viewport._state.auto_sprint_enabled, gravity=float(viewport._session.settings.movement.gravity), walk_speed=float(viewport._session.settings.movement.walk_speed), sprint_speed=float(viewport._session.settings.movement.sprint_speed), jump_v0=float(viewport._session.settings.movement.jump_v0), auto_jump_cooldown_s=float(viewport._session.settings.movement.auto_jump_cooldown_s), fly_speed=float(viewport._session.settings.movement.fly_speed), fly_ascend_speed=float(viewport._session.settings.movement.fly_ascend_speed), fly_descend_speed=float(viewport._session.settings.movement.fly_descend_speed), render_distance_chunks=int(viewport._state.render_distance_chunks), keybinds=viewport._state.keybinds, audio_master=float(viewport._state.audio.master), audio_ambient=float(viewport._state.audio.ambient), audio_block=float(viewport._state.audio.block), audio_player=float(viewport._state.audio.player))

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

def set_animated_textures_enabled(viewport: "GLViewportWidget", on: bool) -> None:
    viewport._state.animated_textures_enabled = bool(on)
    viewport._renderer.set_animated_textures_enabled(bool(viewport._state.animated_textures_enabled))
    sync_hotbar_widgets(viewport)

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

def set_keybind(viewport: "GLViewportWidget", action: str, binding: str) -> None:
    viewport._state.keybinds = viewport._state.keybinds.with_binding(str(action), str(binding))
    viewport._state.normalize()
    sync_input_bindings(viewport)
    sync_hotbar_widgets(viewport)
    sync_settings_values(viewport)

def reset_keybinds(viewport: "GLViewportWidget") -> None:
    viewport._state.keybinds = KeybindSettings()
    viewport._state.normalize()
    sync_input_bindings(viewport)
    sync_hotbar_widgets(viewport)
    sync_settings_values(viewport)

def _replace_audio_preferences(viewport: "GLViewportWidget", *, master: float | None = None, ambient: float | None = None, block: float | None = None, player: float | None = None) -> None:
    current = viewport._state.audio.normalized()
    viewport._state.audio = AudioPreferences(master=float(current.master if master is None else master), ambient=float(current.ambient if ambient is None else ambient), block=float(current.block if block is None else block), player=float(current.player if player is None else player)).normalized()
    sync_audio_preferences(viewport)

def set_master_volume(viewport: "GLViewportWidget", value: float) -> None:
    _replace_audio_preferences(viewport, master=float(value))

def set_ambient_volume(viewport: "GLViewportWidget", value: float) -> None:
    _replace_audio_preferences(viewport, ambient=float(value))

def set_block_volume(viewport: "GLViewportWidget", value: float) -> None:
    _replace_audio_preferences(viewport, block=float(value))

def set_player_volume(viewport: "GLViewportWidget", value: float) -> None:
    _replace_audio_preferences(viewport, player=float(value))