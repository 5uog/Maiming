# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

from ....application.runtime.state.camera_perspective import CAMERA_PERSPECTIVE_FIRST_PERSON, CAMERA_PERSPECTIVE_ORDER
from .cloud_flow_options import cloud_flow_index_for_value
from ...math.scalars import clampf, clampi, round_clampi

if TYPE_CHECKING:
    from .settings_overlay import SettingsOverlay


def _block_signals_set_value(widget, value) -> None:
    widget.blockSignals(True)
    widget.setValue(value)
    widget.blockSignals(False)


def _block_signals_set_text(widget, text: str) -> None:
    widget.blockSignals(True)
    widget.setText(str(text))
    widget.blockSignals(False)


def _sync_toggle(row, checked: bool) -> None:
    row.sync_checked(bool(checked))


def sync_overlay_values(overlay: "SettingsOverlay", **values) -> None:
    fov_int = round_clampi(float(values["fov_deg"]), int(overlay._params.fov_min), int(overlay._params.fov_max))
    _block_signals_set_value(overlay._sld_fov, fov_int)
    overlay._lbl_fov.setText(f"FOV: {fov_int}")

    sensitivity = clampf(float(values["sens_deg_per_px"]), float(overlay._params.sens_min), float(overlay._params.sens_max))
    sensitivity_int = round_clampi(float(sensitivity) * float(overlay._params.sens_scale), int(overlay._params.sens_milli_min), int(overlay._params.sens_milli_max))
    _block_signals_set_value(overlay._sld_sens, sensitivity_int)
    overlay._lbl_sens.setText(f"Mouse sensitivity: {sensitivity:.3f} deg/px")

    render_distance = clampi(int(values["render_distance_chunks"]), int(overlay._params.render_dist_min), int(overlay._params.render_dist_max))
    _block_signals_set_value(overlay._sld_rd, render_distance)
    overlay._lbl_rd.setText(f"Render distance: {render_distance} chunks")

    azimuth = round_clampi(float(values["sun_az_deg"]) % 360.0, int(overlay._params.sun_az_min), int(overlay._params.sun_az_max))
    _block_signals_set_value(overlay._sld_sun_az, azimuth)
    overlay._lbl_sun_az.setText(f"Sun azimuth: {azimuth} deg")

    elevation = round_clampi(float(values["sun_el_deg"]), int(overlay._params.sun_el_min), int(overlay._params.sun_el_max))
    _block_signals_set_value(overlay._sld_sun_el, elevation)
    overlay._lbl_sun_el.setText(f"Sun elevation: {elevation} deg")

    overlay._cb_inv_x.blockSignals(True)
    overlay._cb_inv_y.blockSignals(True)
    overlay._cb_inv_x.setChecked(bool(values["inv_x"]))
    overlay._cb_inv_y.setChecked(bool(values["inv_y"]))
    overlay._cb_inv_x.blockSignals(False)
    overlay._cb_inv_y.blockSignals(False)

    _sync_toggle(overlay._tg_fullscreen, bool(values["fullscreen"]))
    _sync_toggle(overlay._tg_hide_hud, bool(values["hide_hud"]))
    _sync_toggle(overlay._tg_hide_hand, bool(values["hide_hand"]))
    overlay._ctl_arm_rotation_limit_min.set_value(float(values["arm_rotation_limit_min_deg"]))
    overlay._ctl_arm_rotation_limit_max.set_value(float(values["arm_rotation_limit_max_deg"]))
    overlay._ctl_arm_swing_duration.set_value(float(values["arm_swing_duration_s"]))
    overlay._crosshair_editor.set_pixels(values["crosshair_pixels"])
    overlay._crosshair_preview.set_pattern(mode=values["crosshair_mode"], custom_pixels=values["crosshair_pixels"])

    camera_perspective = str(values.get("camera_perspective", CAMERA_PERSPECTIVE_FIRST_PERSON))
    camera_index = 0
    for index, candidate in enumerate(CAMERA_PERSPECTIVE_ORDER):
        if camera_perspective == str(candidate):
            camera_index = int(index)
            break
    overlay._cmb_camera_perspective.blockSignals(True)
    overlay._cmb_camera_perspective.setCurrentIndex(int(camera_index))
    overlay._cmb_camera_perspective.blockSignals(False)

    _sync_toggle(overlay._tg_view_bobbing, bool(values["view_bobbing_enabled"]))
    _sync_toggle(overlay._tg_camera_shake, bool(values["camera_shake_enabled"]))
    _sync_toggle(overlay._tg_animated_textures, bool(values["animated_textures_enabled"]))

    bob_percent = round_clampi(clampf(float(values["view_bobbing_strength"]), 0.0, 1.0) * 100.0, 0, 100)
    _block_signals_set_value(overlay._sld_view_bobbing_strength, bob_percent)
    overlay._lbl_view_bobbing_strength.setText(f"View Bobbing strength: {bob_percent}%")
    overlay._sld_view_bobbing_strength.setEnabled(bool(values["view_bobbing_enabled"]))

    shake_percent = round_clampi(clampf(float(values["camera_shake_strength"]), 0.0, 1.0) * 100.0, 0, 100)
    _block_signals_set_value(overlay._sld_camera_shake_strength, shake_percent)
    overlay._lbl_camera_shake_strength.setText(f"Camera Shake strength: {shake_percent}%")
    overlay._sld_camera_shake_strength.setEnabled(bool(values["camera_shake_enabled"]))

    _sync_toggle(overlay._tg_outline_sel, bool(values["outline_selection"]))
    _sync_toggle(overlay._tg_world_wire, bool(values["world_wire"]))
    _sync_toggle(overlay._tg_shadow_enabled, bool(values["shadow_enabled"]))
    overlay._ctl_block_break_particle_spawn_rate.set_value(float(values["block_break_particle_spawn_rate"]))
    overlay._ctl_block_break_particle_speed_scale.set_value(float(values["block_break_particle_speed_scale"]))
    _sync_toggle(overlay._tg_clouds_enabled, bool(values["clouds_enabled"]))
    _sync_toggle(overlay._tg_cloud_wire, bool(values["cloud_wire"]))

    overlay._cmb_cloud_flow.blockSignals(True)
    overlay._cmb_cloud_flow.setCurrentIndex(int(cloud_flow_index_for_value(str(values["cloud_flow_direction"]))))
    overlay._cmb_cloud_flow.blockSignals(False)

    cloud_density = clampi(int(values["cloud_density"]), 0, 4)
    _block_signals_set_value(overlay._sld_cloud_density, cloud_density)
    overlay._lbl_cloud_density.setText(f"Cloud density: {cloud_density}")

    cloud_seed = clampi(int(values["cloud_seed"]), 0, 9999)
    _block_signals_set_value(overlay._sld_cloud_seed, cloud_seed)
    overlay._lbl_cloud_seed.setText(f"Cloud seed: {cloud_seed}")
    overlay._update_cloud_controls_enabled(bool(values["clouds_enabled"]))

    overlay._btn_mode_toggle.blockSignals(True)
    overlay._btn_mode_toggle.setChecked(bool(values["creative_mode"]))
    overlay._btn_mode_toggle.blockSignals(False)
    overlay._update_mode_toggle_text(bool(values["creative_mode"]))

    _sync_toggle(overlay._tg_auto_jump, bool(values["auto_jump_enabled"]))
    _sync_toggle(overlay._tg_auto_sprint, bool(values["auto_sprint_enabled"]))
    _block_signals_set_text(overlay._name_edit, str(values["player_name"]))
    resolved_name = str(values["resolved_player_name"]).strip()
    explicit_name = str(values["player_name"]).strip()
    if explicit_name:
        overlay._player_name_hint.setText(f"Current session name: {resolved_name}")
    elif resolved_name:
        overlay._player_name_hint.setText(f"Current session name: {resolved_name} (randomized each launch while the field remains blank)")
    else:
        overlay._player_name_hint.setText("Leave the field blank to use a random session name each launch.")
    overlay._ctl_block_break_repeat_interval.set_value(float(values["block_break_repeat_interval_s"]))
    overlay._ctl_block_place_repeat_interval.set_value(float(values["block_place_repeat_interval_s"]))
    overlay._ctl_block_interact_repeat_interval.set_value(float(values["block_interact_repeat_interval_s"]))

    overlay._ctl_gravity.set_value(float(values["gravity"]))
    overlay._ctl_walk_speed.set_value(float(values["walk_speed"]))
    overlay._ctl_sprint_speed.set_value(float(values["sprint_speed"]))
    overlay._ctl_jump_v0.set_value(float(values["jump_v0"]))
    overlay._ctl_auto_jump_cooldown.set_value(float(values["auto_jump_cooldown_s"]))
    overlay._ctl_fly_speed.set_value(float(values["fly_speed"]))
    overlay._ctl_fly_ascend_speed.set_value(float(values["fly_ascend_speed"]))
    overlay._ctl_fly_descend_speed.set_value(float(values["fly_descend_speed"]))

    master_percent = round_clampi(clampf(float(values["audio_master"]), 0.0, 1.0) * 100.0, 0, 100)
    ambient_percent = round_clampi(clampf(float(values["audio_ambient"]), 0.0, 1.0) * 100.0, 0, 100)
    block_percent = round_clampi(clampf(float(values["audio_block"]), 0.0, 1.0) * 100.0, 0, 100)
    player_percent = round_clampi(clampf(float(values["audio_player"]), 0.0, 1.0) * 100.0, 0, 100)

    _block_signals_set_value(overlay._sld_master_volume, master_percent)
    _block_signals_set_value(overlay._sld_ambient_volume, ambient_percent)
    _block_signals_set_value(overlay._sld_block_volume, block_percent)
    _block_signals_set_value(overlay._sld_player_volume, player_percent)
    overlay._lbl_master_volume.setText(f"Master volume: {master_percent}%")
    overlay._lbl_ambient_volume.setText(f"Ambient volume: {ambient_percent}%")
    overlay._lbl_block_volume.setText(f"Block volume: {block_percent}%")
    overlay._lbl_player_volume.setText(f"Player volume: {player_percent}%")

    keybinds = values["keybinds"].normalized()
    for action, row in overlay._keybind_rows.items():
        row.sync_binding_text(keybinds.binding_for_action(str(action)))
