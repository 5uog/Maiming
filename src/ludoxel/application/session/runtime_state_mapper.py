# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/session/runtime_state_mapper.py
from __future__ import annotations

from .audio_preferences import AudioPreferences
from .keybinds import KeybindSettings
from ...domain.play_space import normalize_play_space_id
from ...infrastructure.persistence.app_state_store import AppState, PersistedInventory, PersistedSettings
from .runtime_preferences import RuntimePreferences, coerce_runtime_preferences


def sync_runtime_sun_from_renderer(runtime: RuntimePreferences, renderer) -> None:
    azimuth_deg, elevation_deg = renderer.sun_angles()
    runtime.sun_az_deg = float(azimuth_deg)
    runtime.sun_el_deg = float(elevation_deg)
    runtime.normalize()


def apply_runtime_to_renderer(runtime: RuntimePreferences, renderer) -> None:
    runtime.normalize()
    renderer.set_debug_shadow(bool(runtime.debug_shadow))
    renderer.set_outline_selection_enabled(bool(runtime.outline_selection))
    renderer.set_cloud_wireframe(bool(runtime.cloud_wire))
    renderer.set_cloud_enabled(bool(runtime.cloud_enabled))
    renderer.set_cloud_density(int(runtime.cloud_density))
    renderer.set_cloud_seed(int(runtime.cloud_seed))
    renderer.set_cloud_flow_direction(str(runtime.cloud_flow_direction))
    renderer.set_animated_textures_enabled(bool(runtime.animated_textures_enabled))
    renderer.set_shadow_enabled(bool(runtime.shadow_enabled))
    renderer.set_world_wireframe(bool(runtime.world_wire))
    renderer.set_sun_angles(float(runtime.sun_az_deg), float(runtime.sun_el_deg))


def apply_persisted_settings_to_session(session, settings: PersistedSettings) -> None:
    session.settings.set_fov(float(settings.fov_deg))
    session.settings.set_mouse_sens(float(settings.mouse_sens_deg_per_px))
    session.settings.set_gravity(float(settings.gravity))
    session.settings.set_walk_speed(float(settings.walk_speed))
    session.settings.set_sprint_speed(float(settings.sprint_speed))
    session.settings.set_jump_v0(float(settings.jump_v0))
    session.settings.set_auto_jump_cooldown_s(float(settings.auto_jump_cooldown_s))
    session.settings.set_fly_speed(float(settings.fly_speed))
    session.settings.set_fly_ascend_speed(float(settings.fly_ascend_speed))
    session.settings.set_fly_descend_speed(float(settings.fly_descend_speed))


def runtime_preferences_from_app_state(state: AppState | None, *, runtime: RuntimePreferences | None=None) -> RuntimePreferences:
    out = runtime if runtime is not None else RuntimePreferences()
    if state is None:
        out.normalize()
        return out

    settings = state.settings
    inventory = state.inventory
    out = coerce_runtime_preferences(
        runtime=out,
        current_space_id=normalize_play_space_id(state.current_space_id),
        invert_x=bool(settings.invert_x),
        invert_y=bool(settings.invert_y),
        outline_selection=bool(settings.outline_selection),
        cloud_wire=bool(settings.cloud_wireframe),
        world_wire=bool(settings.world_wireframe),
        shadow_enabled=bool(settings.shadow_enabled),
        sun_az_deg=float(settings.sun_az_deg),
        sun_el_deg=float(settings.sun_el_deg),
        cloud_enabled=bool(settings.cloud_enabled),
        cloud_density=int(settings.cloud_density),
        cloud_seed=int(settings.cloud_seed),
        cloud_flow_direction=str(settings.cloud_flow_direction),
        creative_mode=bool(settings.creative_mode),
        auto_jump_enabled=bool(settings.auto_jump_enabled),
        auto_sprint_enabled=bool(settings.auto_sprint_enabled),
        hide_hud=bool(settings.hide_hud),
        hide_hand=bool(settings.hide_hand),
        fullscreen=bool(settings.fullscreen),
        view_bobbing_enabled=bool(settings.view_bobbing_enabled),
        camera_shake_enabled=bool(settings.camera_shake_enabled),
        view_bobbing_strength=float(settings.view_bobbing_strength),
        camera_shake_strength=float(settings.camera_shake_strength),
        animated_textures_enabled=bool(settings.animated_textures_enabled),
        hud_visible=bool(settings.hud_visible),
        render_distance_chunks=int(settings.render_distance_chunks),
        creative_hotbar_slots=list(inventory.creative_hotbar_slots),
        creative_selected_hotbar_index=int(inventory.creative_selected_hotbar_index),
        survival_hotbar_slots=list(inventory.survival_hotbar_slots),
        survival_selected_hotbar_index=int(inventory.survival_selected_hotbar_index),
        othello_hotbar_slots=list(inventory.othello_hotbar_slots),
        othello_selected_hotbar_index=int(inventory.othello_selected_hotbar_index),
        othello_settings=state.othello_settings,
        keybinds=settings.keybinds if isinstance(settings.keybinds, KeybindSettings) else KeybindSettings.from_dict({}),
        audio=settings.audio if isinstance(settings.audio, AudioPreferences) else AudioPreferences.from_dict({}),
    )
    out.normalize()
    return out


def persisted_settings_from_runtime(runtime: RuntimePreferences, session_settings) -> PersistedSettings:
    runtime.normalize()
    movement = session_settings.movement
    return PersistedSettings(
        fov_deg=float(session_settings.fov_deg),
        mouse_sens_deg_per_px=float(session_settings.mouse_sens_deg_per_px),
        invert_x=bool(runtime.invert_x),
        invert_y=bool(runtime.invert_y),
        outline_selection=bool(runtime.outline_selection),
        cloud_wireframe=bool(runtime.cloud_wire),
        world_wireframe=bool(runtime.world_wire),
        shadow_enabled=bool(runtime.shadow_enabled),
        sun_az_deg=float(runtime.sun_az_deg),
        sun_el_deg=float(runtime.sun_el_deg),
        cloud_enabled=bool(runtime.cloud_enabled),
        cloud_density=int(runtime.cloud_density),
        cloud_seed=int(runtime.cloud_seed),
        cloud_flow_direction=str(runtime.cloud_flow_direction),
        creative_mode=bool(runtime.creative_mode),
        auto_jump_enabled=bool(runtime.auto_jump_enabled),
        auto_sprint_enabled=bool(runtime.auto_sprint_enabled),
        hide_hud=bool(runtime.hide_hud),
        hide_hand=bool(runtime.hide_hand),
        fullscreen=bool(runtime.fullscreen),
        view_bobbing_enabled=bool(runtime.view_bobbing_enabled),
        camera_shake_enabled=bool(runtime.camera_shake_enabled),
        view_bobbing_strength=float(runtime.view_bobbing_strength),
        camera_shake_strength=float(runtime.camera_shake_strength),
        animated_textures_enabled=bool(runtime.animated_textures_enabled),
        gravity=float(movement.gravity),
        walk_speed=float(movement.walk_speed),
        sprint_speed=float(movement.sprint_speed),
        jump_v0=float(movement.jump_v0),
        auto_jump_cooldown_s=float(movement.auto_jump_cooldown_s),
        fly_speed=float(movement.fly_speed),
        fly_ascend_speed=float(movement.fly_ascend_speed),
        fly_descend_speed=float(movement.fly_descend_speed),
        render_distance_chunks=int(runtime.render_distance_chunks),
        hud_visible=bool(runtime.hud_visible),
        keybinds=runtime.keybinds.normalized(),
        audio=runtime.audio.normalized(),
    )


def persisted_inventory_from_runtime(runtime: RuntimePreferences) -> PersistedInventory:
    runtime.normalize()
    return PersistedInventory(
        creative_hotbar_slots=tuple(runtime.creative_hotbar_slots),
        creative_selected_hotbar_index=int(runtime.creative_selected_hotbar_index),
        survival_hotbar_slots=tuple(runtime.survival_hotbar_slots),
        survival_selected_hotbar_index=int(runtime.survival_selected_hotbar_index),
        othello_hotbar_slots=tuple(runtime.othello_hotbar_slots),
        othello_selected_hotbar_index=int(runtime.othello_selected_hotbar_index),
    )
