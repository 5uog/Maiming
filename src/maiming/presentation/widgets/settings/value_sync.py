# FILE: src/maiming/presentation/widgets/settings/value_sync.py
from __future__ import annotations

from .cloud_flow_options import cloud_flow_index_for_value

def _block_signals_set_value(widget, value) -> None:
    widget.blockSignals(True)
    widget.setValue(value)
    widget.blockSignals(False)

def _sync_toggle(row, checked: bool) -> None:
    row.sync_checked(bool(checked))

def sync_overlay_values(overlay, **values) -> None:
    fov_int = int(round(float(values["fov_deg"])))
    fov_int = max(int(overlay._params.fov_min), min(int(overlay._params.fov_max), fov_int))
    _block_signals_set_value(overlay._sld_fov, fov_int)
    overlay._lbl_fov.setText(f"FOV: {fov_int}")

    sensitivity = max(float(overlay._params.sens_min), min(float(overlay._params.sens_max), float(values["sens_deg_per_px"])))
    sensitivity_int = int(round(sensitivity * float(overlay._params.sens_scale)))
    sensitivity_int = max(int(overlay._params.sens_milli_min), min(int(overlay._params.sens_milli_max), sensitivity_int))
    _block_signals_set_value(overlay._sld_sens, sensitivity_int)
    overlay._lbl_sens.setText(f"Mouse sensitivity: {sensitivity:.3f} deg/px")

    render_distance = int(max(int(overlay._params.render_dist_min), min(int(overlay._params.render_dist_max), int(values["render_distance_chunks"]))))
    _block_signals_set_value(overlay._sld_rd, render_distance)
    overlay._lbl_rd.setText(f"Render distance: {render_distance} chunks")

    azimuth = int(round(float(values["sun_az_deg"]) % 360.0))
    azimuth = max(int(overlay._params.sun_az_min), min(int(overlay._params.sun_az_max), azimuth))
    _block_signals_set_value(overlay._sld_sun_az, azimuth)
    overlay._lbl_sun_az.setText(f"Sun azimuth: {azimuth} deg")

    elevation = int(round(float(values["sun_el_deg"])))
    elevation = max(int(overlay._params.sun_el_min), min(int(overlay._params.sun_el_max), elevation))
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
    _sync_toggle(overlay._tg_view_bobbing, bool(values["view_bobbing_enabled"]))
    _sync_toggle(overlay._tg_camera_shake, bool(values["camera_shake_enabled"]))

    bob_percent = int(round(max(0.0, min(1.0, float(values["view_bobbing_strength"]))) * 100.0))
    _block_signals_set_value(overlay._sld_view_bobbing_strength, bob_percent)
    overlay._lbl_view_bobbing_strength.setText(f"View Bobbing strength: {bob_percent}%")
    overlay._sld_view_bobbing_strength.setEnabled(bool(values["view_bobbing_enabled"]))

    shake_percent = int(round(max(0.0, min(1.0, float(values["camera_shake_strength"]))) * 100.0))
    _block_signals_set_value(overlay._sld_camera_shake_strength, shake_percent)
    overlay._lbl_camera_shake_strength.setText(f"Camera Shake strength: {shake_percent}%")
    overlay._sld_camera_shake_strength.setEnabled(bool(values["camera_shake_enabled"]))

    _sync_toggle(overlay._tg_outline_sel, bool(values["outline_selection"]))
    _sync_toggle(overlay._tg_world_wire, bool(values["world_wire"]))
    _sync_toggle(overlay._tg_shadow_enabled, bool(values["shadow_enabled"]))
    _sync_toggle(overlay._tg_clouds_enabled, bool(values["clouds_enabled"]))
    _sync_toggle(overlay._tg_cloud_wire, bool(values["cloud_wire"]))

    overlay._cmb_cloud_flow.blockSignals(True)
    overlay._cmb_cloud_flow.setCurrentIndex(int(cloud_flow_index_for_value(str(values["cloud_flow_direction"]))))
    overlay._cmb_cloud_flow.blockSignals(False)

    cloud_density = int(max(0, min(4, int(values["cloud_density"]))))
    _block_signals_set_value(overlay._sld_cloud_density, cloud_density)
    overlay._lbl_cloud_density.setText(f"Cloud density: {cloud_density}")

    cloud_seed = int(max(0, min(9999, int(values["cloud_seed"]))))
    _block_signals_set_value(overlay._sld_cloud_seed, cloud_seed)
    overlay._lbl_cloud_seed.setText(f"Cloud seed: {cloud_seed}")

    overlay._btn_mode_toggle.blockSignals(True)
    overlay._btn_mode_toggle.setChecked(bool(values["creative_mode"]))
    overlay._btn_mode_toggle.blockSignals(False)
    overlay._update_mode_toggle_text(bool(values["creative_mode"]))

    _sync_toggle(overlay._tg_auto_jump, bool(values["auto_jump_enabled"]))
    _sync_toggle(overlay._tg_auto_sprint, bool(values["auto_sprint_enabled"]))

    overlay._ctl_gravity.set_value(float(values["gravity"]))
    overlay._ctl_walk_speed.set_value(float(values["walk_speed"]))
    overlay._ctl_sprint_speed.set_value(float(values["sprint_speed"]))
    overlay._ctl_jump_v0.set_value(float(values["jump_v0"]))
    overlay._ctl_auto_jump_cooldown.set_value(float(values["auto_jump_cooldown_s"]))
    overlay._ctl_fly_speed.set_value(float(values["fly_speed"]))
    overlay._ctl_fly_ascend_speed.set_value(float(values["fly_ascend_speed"]))
    overlay._ctl_fly_descend_speed.set_value(float(values["fly_descend_speed"]))