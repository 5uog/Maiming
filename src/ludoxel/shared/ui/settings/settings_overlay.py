# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from ....application.runtime.keybinds import CONTROL_SECTION_GAMEPLAY, CONTROL_SECTION_MOVEMENT, HOTBAR_ACTIONS, action_display_name
from ....application.runtime.state.camera_perspective import CAMERA_PERSPECTIVE_FIRST_PERSON, CAMERA_PERSPECTIVE_LABELS, CAMERA_PERSPECTIVE_ORDER
from ....application.runtime.state.runtime_preferences import RuntimePreferences
from ..config.pause_overlay_params import DEFAULT_PAUSE_OVERLAY_PARAMS, PauseOverlayParams
from ...math.scalars import clampf, clampi, round_clampi
from ...opengl.runtime.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION
from ...world.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from .widgets.advanced_scalar_control import AdvancedScalarControl
from .widgets.controls import BedrockToggleRow, KeybindRow, WheelPassthroughSlider
from .cloud_flow_options import CLOUD_FLOW_OPTIONS, cloud_flow_index_for_value
from .widgets.crosshair_widgets import CrosshairPixelEditor, CrosshairPreviewWidget


def _block_signals_set_value(widget, value) -> None:
    widget.blockSignals(True)
    widget.setValue(value)
    widget.blockSignals(False)


def _sync_toggle(row, checked: bool) -> None:
    row.sync_checked(bool(checked))


def _sync_overlay_values(overlay, **values) -> None:
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
    overlay._ctl_block_break_repeat_interval.set_value(float(values["block_break_repeat_interval_s"]))
    overlay._ctl_block_place_repeat_interval.set_value(float(values["block_place_repeat_interval_s"]))

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


def _build_video_tab(overlay) -> None:
    scroll, host, layout = overlay._make_scroll_page()
    layout.addWidget(overlay._section(host, "Display"))
    overlay._tg_fullscreen = overlay._add_toggle(layout, host, "Fullscreen", overlay.fullscreen_changed.emit)
    overlay._tg_hide_hud = overlay._add_toggle(layout, host, "Hide HUD", overlay.hide_hud_changed.emit)
    overlay._tg_hide_hand = overlay._add_toggle(layout, host, "Hide Hand", overlay.hide_hand_changed.emit)
    overlay._tg_view_bobbing = overlay._add_toggle(layout, host, "View Bobbing", overlay._on_view_bobbing_toggled)

    bob_row = QVBoxLayout()
    overlay._lbl_view_bobbing_strength = QLabel("View Bobbing strength: 35%", host)
    overlay._lbl_view_bobbing_strength.setObjectName("valueLabel")
    overlay._sld_view_bobbing_strength = overlay._new_slider(host, int(overlay._params.bob_strength_percent_min), int(overlay._params.bob_strength_percent_max))
    overlay._sld_view_bobbing_strength.valueChanged.connect(overlay._on_view_bobbing_strength)
    bob_row.addWidget(overlay._lbl_view_bobbing_strength)
    bob_row.addWidget(overlay._sld_view_bobbing_strength)
    layout.addLayout(bob_row)

    overlay._tg_camera_shake = overlay._add_toggle(layout, host, "Camera Shake", overlay._on_camera_shake_toggled)
    shake_row = QVBoxLayout()
    overlay._lbl_camera_shake_strength = QLabel("Camera Shake strength: 20%", host)
    overlay._lbl_camera_shake_strength.setObjectName("valueLabel")
    overlay._sld_camera_shake_strength = overlay._new_slider(host, int(overlay._params.shake_strength_percent_min), int(overlay._params.shake_strength_percent_max))
    overlay._sld_camera_shake_strength.valueChanged.connect(overlay._on_camera_shake_strength)
    shake_row.addWidget(overlay._lbl_camera_shake_strength)
    shake_row.addWidget(overlay._sld_camera_shake_strength)
    layout.addLayout(shake_row)

    fov_row = QVBoxLayout()
    overlay._lbl_fov = QLabel("FOV: 80", host)
    overlay._lbl_fov.setObjectName("valueLabel")
    overlay._sld_fov = overlay._new_slider(host, int(overlay._params.fov_min), int(overlay._params.fov_max))
    overlay._sld_fov.valueChanged.connect(overlay._on_fov)
    fov_row.addWidget(overlay._lbl_fov)
    fov_row.addWidget(overlay._sld_fov)
    layout.addLayout(fov_row)

    camera_row = QHBoxLayout()
    overlay._lbl_camera_perspective = QLabel("Camera perspective", host)
    overlay._lbl_camera_perspective.setObjectName("valueLabel")
    camera_row.addWidget(overlay._lbl_camera_perspective)
    overlay._cmb_camera_perspective = QComboBox(host)
    for value in CAMERA_PERSPECTIVE_ORDER:
        overlay._cmb_camera_perspective.addItem(str(CAMERA_PERSPECTIVE_LABELS[str(value)]), userData=str(value))
    overlay._cmb_camera_perspective.currentIndexChanged.connect(overlay._on_camera_perspective)
    camera_row.addWidget(overlay._cmb_camera_perspective)
    camera_row.addStretch(1)
    layout.addLayout(camera_row)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Crosshair"))

    overlay._lbl_crosshair_help = QLabel("Draw a custom 16x16 crosshair with the left mouse button, erase with the right mouse button, or use Clear Board to restore the default Minecraft-style crosshair and reset the editor board.", host)
    overlay._lbl_crosshair_help.setObjectName("valueLabel")
    overlay._lbl_crosshair_help.setWordWrap(True)
    layout.addWidget(overlay._lbl_crosshair_help)

    crosshair_preview_row = QHBoxLayout()
    overlay._crosshair_preview = CrosshairPreviewWidget(host)
    crosshair_preview_row.addWidget(overlay._crosshair_preview, stretch=0)

    crosshair_buttons = QVBoxLayout()
    overlay._btn_crosshair_clear = QPushButton("Clear Board", host)
    overlay._btn_crosshair_clear.setObjectName("menuBtn")
    overlay._btn_crosshair_clear.clicked.connect(overlay.crosshair_clear_requested.emit)
    crosshair_buttons.addWidget(overlay._btn_crosshair_clear)
    crosshair_buttons.addStretch(1)
    crosshair_preview_row.addLayout(crosshair_buttons, stretch=0)
    crosshair_preview_row.addStretch(1)
    layout.addLayout(crosshair_preview_row)

    overlay._crosshair_editor = CrosshairPixelEditor(host)
    overlay._crosshair_editor.pixels_changed.connect(overlay.crosshair_pixels_changed.emit)
    layout.addWidget(overlay._crosshair_editor)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "World"))

    rd_row = QVBoxLayout()
    overlay._lbl_rd = QLabel("Render distance: 6 chunks", host)
    overlay._lbl_rd.setObjectName("valueLabel")
    overlay._sld_rd = overlay._new_slider(host, int(overlay._params.render_dist_min), int(overlay._params.render_dist_max))
    overlay._sld_rd.valueChanged.connect(overlay._on_rd)
    rd_row.addWidget(overlay._lbl_rd)
    rd_row.addWidget(overlay._sld_rd)
    layout.addLayout(rd_row)

    overlay._tg_animated_textures = overlay._add_toggle(layout, host, "Animated Textures", overlay.animated_textures_changed.emit)
    overlay._tg_outline_sel = overlay._add_toggle(layout, host, "Outline selection", overlay.outline_selection_changed.emit)
    overlay._tg_world_wire = overlay._add_toggle(layout, host, "World wireframe", overlay.world_wireframe_changed.emit)
    overlay._tg_shadow_enabled = overlay._add_toggle(layout, host, "Shadow map", overlay.shadow_enabled_changed.emit)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Particles"))

    overlay._ctl_block_break_particle_spawn_rate = AdvancedScalarControl(title="Break particle spawn rate", min_value=float(overlay._params.block_break_particle_spawn_rate_milli_min) / float(overlay._params.block_break_particle_spawn_rate_scale), max_value=float(overlay._params.block_break_particle_spawn_rate_milli_max) / float(overlay._params.block_break_particle_spawn_rate_scale), slider_scale=float(overlay._params.block_break_particle_spawn_rate_scale), decimals=int(overlay._params.block_break_particle_spawn_rate_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_BREAK_PARTICLE_SPAWN_RATE), parent=host)
    overlay._ctl_block_break_particle_spawn_rate.value_changed.connect(overlay.block_break_particle_spawn_rate_changed.emit)
    layout.addWidget(overlay._ctl_block_break_particle_spawn_rate)

    overlay._ctl_block_break_particle_speed_scale = AdvancedScalarControl(title="Break particle speed", min_value=float(overlay._params.block_break_particle_speed_milli_min) / float(overlay._params.block_break_particle_speed_scale), max_value=float(overlay._params.block_break_particle_speed_milli_max) / float(overlay._params.block_break_particle_speed_scale), slider_scale=float(overlay._params.block_break_particle_speed_scale), decimals=int(overlay._params.block_break_particle_speed_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_BREAK_PARTICLE_SPEED_SCALE), parent=host)
    overlay._ctl_block_break_particle_speed_scale.value_changed.connect(overlay.block_break_particle_speed_scale_changed.emit)
    layout.addWidget(overlay._ctl_block_break_particle_speed_scale)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Clouds"))

    overlay._tg_clouds_enabled = overlay._add_toggle(layout, host, "Show clouds", overlay._on_clouds_toggled)
    overlay._tg_cloud_wire = overlay._add_toggle(layout, host, "Cloud wireframe", overlay.cloud_wireframe_changed.emit)

    cloud_flow_row = QHBoxLayout()
    overlay._lbl_cloud_flow = QLabel("Cloud flow direction", host)
    overlay._lbl_cloud_flow.setObjectName("valueLabel")
    cloud_flow_row.addWidget(overlay._lbl_cloud_flow)
    overlay._cmb_cloud_flow = QComboBox(host)
    for value, label in CLOUD_FLOW_OPTIONS:
        overlay._cmb_cloud_flow.addItem(str(label), userData=str(value))
    overlay._cmb_cloud_flow.currentIndexChanged.connect(overlay._on_cloud_flow_direction)
    cloud_flow_row.addWidget(overlay._cmb_cloud_flow)
    cloud_flow_row.addStretch(1)
    layout.addLayout(cloud_flow_row)

    cloud_density_row = QVBoxLayout()
    overlay._lbl_cloud_density = QLabel("Cloud density: 1", host)
    overlay._lbl_cloud_density.setObjectName("valueLabel")
    overlay._sld_cloud_density = overlay._new_slider(host, 0, 4)
    overlay._sld_cloud_density.valueChanged.connect(overlay._on_cloud_density)
    cloud_density_row.addWidget(overlay._lbl_cloud_density)
    cloud_density_row.addWidget(overlay._sld_cloud_density)
    layout.addLayout(cloud_density_row)

    cloud_seed_row = QVBoxLayout()
    overlay._lbl_cloud_seed = QLabel("Cloud seed: 1337", host)
    overlay._lbl_cloud_seed.setObjectName("valueLabel")
    overlay._sld_cloud_seed = overlay._new_slider(host, 0, 9999)
    overlay._sld_cloud_seed.valueChanged.connect(overlay._on_cloud_seed)
    cloud_seed_row.addWidget(overlay._lbl_cloud_seed)
    cloud_seed_row.addWidget(overlay._sld_cloud_seed)
    layout.addLayout(cloud_seed_row)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Sun"))

    sun_az_row = QVBoxLayout()
    overlay._lbl_sun_az = QLabel("Sun azimuth: 45 deg", host)
    overlay._lbl_sun_az.setObjectName("valueLabel")
    overlay._sld_sun_az = overlay._new_slider(host, int(overlay._params.sun_az_min), int(overlay._params.sun_az_max))
    overlay._sld_sun_az.valueChanged.connect(overlay._on_sun_az)
    sun_az_row.addWidget(overlay._lbl_sun_az)
    sun_az_row.addWidget(overlay._sld_sun_az)
    layout.addLayout(sun_az_row)

    sun_el_row = QVBoxLayout()
    overlay._lbl_sun_el = QLabel("Sun elevation: 60 deg", host)
    overlay._lbl_sun_el.setObjectName("valueLabel")
    overlay._sld_sun_el = overlay._new_slider(host, int(overlay._params.sun_el_min), int(overlay._params.sun_el_max))
    overlay._sld_sun_el.valueChanged.connect(overlay._on_sun_el)
    sun_el_row.addWidget(overlay._lbl_sun_el)
    sun_el_row.addWidget(overlay._sld_sun_el)
    layout.addLayout(sun_el_row)

    layout.addStretch(1)
    overlay._stack.addWidget(scroll)


def _build_controls_tab(overlay) -> None:
    scroll, host, layout = overlay._make_scroll_page()
    layout.addWidget(overlay._section(host, "Mouse"))

    sens_row = QVBoxLayout()
    overlay._lbl_sens = QLabel("Mouse sensitivity: 0.090 deg/px", host)
    overlay._lbl_sens.setObjectName("valueLabel")
    overlay._sld_sens = overlay._new_slider(host, int(overlay._params.sens_milli_min), int(overlay._params.sens_milli_max))
    overlay._sld_sens.valueChanged.connect(overlay._on_sens)
    sens_row.addWidget(overlay._lbl_sens)
    sens_row.addWidget(overlay._sld_sens)
    layout.addLayout(sens_row)

    invert_row = QHBoxLayout()
    overlay._cb_inv_x = QCheckBox("Invert X", host)
    overlay._cb_inv_y = QCheckBox("Invert Y", host)
    overlay._cb_inv_x.toggled.connect(overlay.invert_x_changed.emit)
    overlay._cb_inv_y.toggled.connect(overlay.invert_y_changed.emit)
    invert_row.addWidget(overlay._cb_inv_x)
    invert_row.addWidget(overlay._cb_inv_y)
    invert_row.addStretch(1)
    layout.addLayout(invert_row)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Movement Keys"))
    for action in CONTROL_SECTION_MOVEMENT:
        overlay._add_keybind_row(layout, host, str(action))

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Gameplay Keys"))
    for action in CONTROL_SECTION_GAMEPLAY:
        overlay._add_keybind_row(layout, host, str(action))

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Hotbar Keys"))
    for action in HOTBAR_ACTIONS:
        overlay._add_keybind_row(layout, host, str(action))

    row_reset = QHBoxLayout()
    row_reset.addStretch(1)
    btn_reset_bindings = QPushButton("Reset Keybinds", host)
    btn_reset_bindings.setObjectName("menuBtn")
    btn_reset_bindings.clicked.connect(overlay.keybind_reset_requested.emit)
    row_reset.addWidget(btn_reset_bindings)
    layout.addLayout(row_reset)

    layout.addStretch(1)
    overlay._stack.addWidget(scroll)


def _build_audio_tab(overlay) -> None:
    scroll, host, layout = overlay._make_scroll_page()
    layout.addWidget(overlay._section(host, "Mixer"))

    overlay._lbl_master_volume = QLabel("Master volume: 100%", host)
    overlay._lbl_master_volume.setObjectName("valueLabel")
    overlay._sld_master_volume = overlay._new_slider(host, 0, 100)
    overlay._sld_master_volume.valueChanged.connect(overlay._on_master_volume)
    layout.addWidget(overlay._lbl_master_volume)
    layout.addWidget(overlay._sld_master_volume)

    overlay._lbl_ambient_volume = QLabel("Ambient volume: 100%", host)
    overlay._lbl_ambient_volume.setObjectName("valueLabel")
    overlay._sld_ambient_volume = overlay._new_slider(host, 0, 100)
    overlay._sld_ambient_volume.valueChanged.connect(overlay._on_ambient_volume)
    layout.addWidget(overlay._lbl_ambient_volume)
    layout.addWidget(overlay._sld_ambient_volume)

    overlay._lbl_block_volume = QLabel("Block volume: 100%", host)
    overlay._lbl_block_volume.setObjectName("valueLabel")
    overlay._sld_block_volume = overlay._new_slider(host, 0, 100)
    overlay._sld_block_volume.valueChanged.connect(overlay._on_block_volume)
    layout.addWidget(overlay._lbl_block_volume)
    layout.addWidget(overlay._sld_block_volume)

    overlay._lbl_player_volume = QLabel("Player volume: 100%", host)
    overlay._lbl_player_volume.setObjectName("valueLabel")
    overlay._sld_player_volume = overlay._new_slider(host, 0, 100)
    overlay._sld_player_volume.valueChanged.connect(overlay._on_player_volume)
    layout.addWidget(overlay._lbl_player_volume)
    layout.addWidget(overlay._sld_player_volume)

    layout.addStretch(1)
    overlay._stack.addWidget(scroll)


def _build_game_tab(overlay) -> None:
    scroll, host, layout = overlay._make_scroll_page()
    layout.addWidget(overlay._section(host, "Game Mode"))

    overlay._btn_mode_toggle = QPushButton(host)
    overlay._btn_mode_toggle.setObjectName("modeToggle")
    overlay._btn_mode_toggle.setCheckable(True)
    overlay._btn_mode_toggle.clicked.connect(overlay._on_mode_toggle_clicked)
    layout.addWidget(overlay._btn_mode_toggle)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Player Options"))

    overlay._tg_auto_jump = overlay._add_toggle(layout, host, "Auto-Jump", overlay.auto_jump_changed.emit)
    overlay._tg_auto_sprint = overlay._add_toggle(layout, host, "Auto-Sprint", overlay.auto_sprint_changed.emit)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Interaction Parameters"))

    overlay._ctl_block_break_repeat_interval = AdvancedScalarControl(title="Break repeat interval", min_value=float(overlay._params.block_break_repeat_interval_milli_min) / float(overlay._params.block_break_repeat_interval_scale), max_value=float(overlay._params.block_break_repeat_interval_milli_max) / float(overlay._params.block_break_repeat_interval_scale), slider_scale=float(overlay._params.block_break_repeat_interval_scale), decimals=int(overlay._params.block_break_repeat_interval_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_BREAK_REPEAT_INTERVAL_S), parent=host)
    overlay._ctl_block_break_repeat_interval.value_changed.connect(overlay.block_break_repeat_interval_changed.emit)
    layout.addWidget(overlay._ctl_block_break_repeat_interval)

    overlay._ctl_block_place_repeat_interval = AdvancedScalarControl(title="Place repeat interval", min_value=float(overlay._params.block_place_repeat_interval_milli_min) / float(overlay._params.block_place_repeat_interval_scale), max_value=float(overlay._params.block_place_repeat_interval_milli_max) / float(overlay._params.block_place_repeat_interval_scale), slider_scale=float(overlay._params.block_place_repeat_interval_scale), decimals=int(overlay._params.block_place_repeat_interval_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_PLACE_REPEAT_INTERVAL_S), parent=host)
    overlay._ctl_block_place_repeat_interval.value_changed.connect(overlay.block_place_repeat_interval_changed.emit)
    layout.addWidget(overlay._ctl_block_place_repeat_interval)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Movement Parameters"))

    overlay._ctl_gravity = AdvancedScalarControl(title="Gravity", min_value=float(overlay._params.gravity_milli_min) / float(overlay._params.gravity_scale), max_value=float(overlay._params.gravity_milli_max) / float(overlay._params.gravity_scale), slider_scale=float(overlay._params.gravity_scale), decimals=int(overlay._params.gravity_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.gravity), parent=host)
    overlay._ctl_gravity.value_changed.connect(overlay.gravity_changed.emit)
    layout.addWidget(overlay._ctl_gravity)

    overlay._ctl_walk_speed = AdvancedScalarControl(title="Walk speed", min_value=float(overlay._params.walk_speed_milli_min) / float(overlay._params.walk_speed_scale), max_value=float(overlay._params.walk_speed_milli_max) / float(overlay._params.walk_speed_scale), slider_scale=float(overlay._params.walk_speed_scale), decimals=int(overlay._params.walk_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.walk_speed), parent=host)
    overlay._ctl_walk_speed.value_changed.connect(overlay.walk_speed_changed.emit)
    layout.addWidget(overlay._ctl_walk_speed)

    overlay._ctl_sprint_speed = AdvancedScalarControl(title="Sprint speed", min_value=float(overlay._params.sprint_speed_milli_min) / float(overlay._params.sprint_speed_scale), max_value=float(overlay._params.sprint_speed_milli_max) / float(overlay._params.sprint_speed_scale), slider_scale=float(overlay._params.sprint_speed_scale), decimals=int(overlay._params.sprint_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.sprint_speed), parent=host)
    overlay._ctl_sprint_speed.value_changed.connect(overlay.sprint_speed_changed.emit)
    layout.addWidget(overlay._ctl_sprint_speed)

    overlay._ctl_jump_v0 = AdvancedScalarControl(title="Jump velocity", min_value=float(overlay._params.jump_v0_milli_min) / float(overlay._params.jump_v0_scale), max_value=float(overlay._params.jump_v0_milli_max) / float(overlay._params.jump_v0_scale), slider_scale=float(overlay._params.jump_v0_scale), decimals=int(overlay._params.jump_v0_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.jump_v0), parent=host)
    overlay._ctl_jump_v0.value_changed.connect(overlay.jump_v0_changed.emit)
    layout.addWidget(overlay._ctl_jump_v0)

    overlay._ctl_auto_jump_cooldown = AdvancedScalarControl(title="Auto-jump cooldown", min_value=float(overlay._params.auto_jump_cooldown_milli_min) / float(overlay._params.auto_jump_cooldown_scale), max_value=float(overlay._params.auto_jump_cooldown_milli_max) / float(overlay._params.auto_jump_cooldown_scale), slider_scale=float(overlay._params.auto_jump_cooldown_scale), decimals=int(overlay._params.auto_jump_cooldown_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s), parent=host)
    overlay._ctl_auto_jump_cooldown.value_changed.connect(overlay.auto_jump_cooldown_changed.emit)
    layout.addWidget(overlay._ctl_auto_jump_cooldown)

    layout.addWidget(overlay._section(host, "Flight Parameters"))

    overlay._ctl_fly_speed = AdvancedScalarControl(title="Flight speed", min_value=float(overlay._params.fly_speed_milli_min) / float(overlay._params.fly_speed_scale), max_value=float(overlay._params.fly_speed_milli_max) / float(overlay._params.fly_speed_scale), slider_scale=float(overlay._params.fly_speed_scale), decimals=int(overlay._params.fly_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.fly_speed), parent=host)
    overlay._ctl_fly_speed.value_changed.connect(overlay.fly_speed_changed.emit)
    layout.addWidget(overlay._ctl_fly_speed)

    overlay._ctl_fly_ascend_speed = AdvancedScalarControl(title="Ascend speed", min_value=float(overlay._params.fly_ascend_speed_milli_min) / float(overlay._params.fly_ascend_speed_scale), max_value=float(overlay._params.fly_ascend_speed_milli_max) / float(overlay._params.fly_ascend_speed_scale), slider_scale=float(overlay._params.fly_ascend_speed_scale), decimals=int(overlay._params.fly_ascend_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed), parent=host)
    overlay._ctl_fly_ascend_speed.value_changed.connect(overlay.fly_ascend_speed_changed.emit)
    layout.addWidget(overlay._ctl_fly_ascend_speed)

    overlay._ctl_fly_descend_speed = AdvancedScalarControl(title="Descend speed", min_value=float(overlay._params.fly_descend_speed_milli_min) / float(overlay._params.fly_descend_speed_scale), max_value=float(overlay._params.fly_descend_speed_milli_max) / float(overlay._params.fly_descend_speed_scale), slider_scale=float(overlay._params.fly_descend_speed_scale), decimals=int(overlay._params.fly_descend_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed), parent=host)
    overlay._ctl_fly_descend_speed.value_changed.connect(overlay.fly_descend_speed_changed.emit)
    layout.addWidget(overlay._ctl_fly_descend_speed)

    layout.addWidget(overlay._sep(host))

    btn_reset_adv = QPushButton("Reset Advanced to Defaults", host)
    btn_reset_adv.setObjectName("menuBtn")
    btn_reset_adv.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btn_reset_adv.clicked.connect(overlay.advanced_reset_requested.emit)
    layout.addWidget(btn_reset_adv)

    layout.addStretch(1)
    overlay._stack.addWidget(scroll)


class SettingsOverlay(QDialog):
    back_requested = pyqtSignal()
    fov_changed = pyqtSignal(float)
    sens_changed = pyqtSignal(float)
    invert_x_changed = pyqtSignal(bool)
    invert_y_changed = pyqtSignal(bool)
    fullscreen_changed = pyqtSignal(bool)
    hide_hud_changed = pyqtSignal(bool)
    hide_hand_changed = pyqtSignal(bool)
    crosshair_pixels_changed = pyqtSignal(object)
    crosshair_clear_requested = pyqtSignal()
    camera_perspective_changed = pyqtSignal(str)
    view_bobbing_changed = pyqtSignal(bool)
    camera_shake_changed = pyqtSignal(bool)
    view_bobbing_strength_changed = pyqtSignal(float)
    camera_shake_strength_changed = pyqtSignal(float)
    animated_textures_changed = pyqtSignal(bool)
    outline_selection_changed = pyqtSignal(bool)
    cloud_wireframe_changed = pyqtSignal(bool)
    clouds_enabled_changed = pyqtSignal(bool)
    cloud_density_changed = pyqtSignal(int)
    cloud_seed_changed = pyqtSignal(int)
    cloud_flow_direction_changed = pyqtSignal(str)
    world_wireframe_changed = pyqtSignal(bool)
    shadow_enabled_changed = pyqtSignal(bool)
    sun_azimuth_changed = pyqtSignal(float)
    sun_elevation_changed = pyqtSignal(float)
    creative_mode_changed = pyqtSignal(bool)
    auto_jump_changed = pyqtSignal(bool)
    auto_sprint_changed = pyqtSignal(bool)
    block_break_repeat_interval_changed = pyqtSignal(float)
    block_place_repeat_interval_changed = pyqtSignal(float)
    block_break_particle_spawn_rate_changed = pyqtSignal(float)
    block_break_particle_speed_scale_changed = pyqtSignal(float)
    gravity_changed = pyqtSignal(float)
    walk_speed_changed = pyqtSignal(float)
    sprint_speed_changed = pyqtSignal(float)
    jump_v0_changed = pyqtSignal(float)
    auto_jump_cooldown_changed = pyqtSignal(float)
    fly_speed_changed = pyqtSignal(float)
    fly_ascend_speed_changed = pyqtSignal(float)
    fly_descend_speed_changed = pyqtSignal(float)
    advanced_reset_requested = pyqtSignal()
    render_distance_changed = pyqtSignal(int)
    keybind_changed = pyqtSignal(str, str)
    keybind_reset_requested = pyqtSignal()
    master_volume_changed = pyqtSignal(float)
    ambient_volume_changed = pyqtSignal(float)
    block_volume_changed = pyqtSignal(float)
    player_volume_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None=None, params: PauseOverlayParams=DEFAULT_PAUSE_OVERLAY_PARAMS, *, as_window: bool=False) -> None:
        super().__init__(parent)
        self._params = params
        self._keybind_rows: dict[str, KeybindRow] = {}
        self._deferred_reveal_pending: bool = False
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("settingsRoot")
        self._as_window = bool(as_window)
        self.setProperty("detachedWindow", bool(self._as_window))
        if bool(self._as_window):
            self.setWindowFlag(Qt.WindowType.Dialog, True)
            self.setWindowFlag(Qt.WindowType.CustomizeWindowHint, True)
            self.setWindowFlag(Qt.WindowType.WindowTitleHint, True)
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.setWindowTitle("Settings")
            self.resize(1120, 780)
            self.setMinimumSize(1000, 720)
            self.setAutoFillBackground(True)
            self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            palette = self.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#181818"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#181818"))
            self.setPalette(palette)

        root = QVBoxLayout(self)
        if bool(self._as_window):
            root.setContentsMargins(0, 0, 0, 0)
        else:
            root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)
        if not bool(self._as_window):
            root.addStretch(1)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setMinimumWidth(960)
        panel.setMinimumHeight(620)

        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self._sidebar = QWidget(panel)
        self._sidebar.setObjectName("settingsSidebar")
        self._sidebar.setMinimumWidth(236)
        self._sidebar.setMaximumWidth(280)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(0, 12, 0, 12)
        sidebar_layout.setSpacing(0)
        self._tab_video = self._make_tab_button("Video", 0, self._sidebar)
        self._tab_controls = self._make_tab_button("Controls", 1, self._sidebar)
        self._tab_audio = self._make_tab_button("Audio", 2, self._sidebar)
        self._tab_game = self._make_tab_button("Game Player", 3, self._sidebar)
        sidebar_layout.addWidget(self._tab_video)
        sidebar_layout.addWidget(self._tab_controls)
        sidebar_layout.addWidget(self._tab_audio)
        sidebar_layout.addWidget(self._tab_game)
        sidebar_layout.addStretch(1)

        self._content = QWidget(panel)
        self._content.setObjectName("settingsContent")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(0)
        self._stack = QStackedWidget(self._content)
        self._stack.setObjectName("settingsStack")
        content_layout.addWidget(self._stack, stretch=1)

        panel_layout.addWidget(self._sidebar, stretch=2)
        panel_layout.addWidget(self._content, stretch=8)

        _build_video_tab(self)
        _build_controls_tab(self)
        _build_audio_tab(self)
        _build_game_tab(self)
        self._set_tab(0)

        if bool(self._as_window):
            root.addWidget(panel, stretch=1)
        else:
            root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
            root.addStretch(1)

    def prepare_to_show(self) -> None:
        if not bool(self._as_window):
            return
        self._deferred_reveal_pending = True
        self.setWindowOpacity(0.0)
        self.winId()
        self.ensurePolished()
        layout = self.layout()
        if layout is not None:
            layout.activate()
        self.adjustSize()
        self.updateGeometry()

    def showEvent(self, event) -> None:
        if bool(self._as_window) and bool(self._deferred_reveal_pending):
            self.setWindowOpacity(0.0)
            QTimer.singleShot(0, self._finish_deferred_reveal)
        super().showEvent(event)

    def _finish_deferred_reveal(self) -> None:
        if not bool(self._deferred_reveal_pending):
            return
        self._deferred_reveal_pending = False
        if not self.isVisible():
            return
        self.setWindowOpacity(1.0)

    def _make_tab_button(self, text: str, index: int, parent: QWidget) -> QPushButton:
        button = QPushButton(text, parent)
        button.setObjectName("navBtn")
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setAutoDefault(False)
        button.setDefault(False)
        button.setFlat(True)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setFixedHeight(64)
        button.clicked.connect(lambda _checked=False, i=index: self._set_tab(i))
        return button

    def _make_scroll_page(self) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea(self._stack)
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        host = QWidget(scroll)
        host.setObjectName("settingsPage")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)
        scroll.setWidget(host)
        return scroll, host, layout

    @staticmethod
    def _sep(parent: QWidget) -> QFrame:
        separator = QFrame(parent)
        separator.setObjectName("sep")
        separator.setFrameShape(QFrame.Shape.HLine)
        return separator

    @staticmethod
    def _section(parent: QWidget, text: str):
        from PyQt6.QtWidgets import QLabel

        label = QLabel(text, parent)
        label.setObjectName("sectionTitle")
        return label

    def _current_cloud_flow_value(self) -> str:
        data = self._cmb_cloud_flow.currentData()
        return str(DEFAULT_CLOUD_FLOW_DIRECTION) if data is None else str(data)

    def _current_camera_perspective_value(self) -> str:
        data = self._cmb_camera_perspective.currentData()
        return str(CAMERA_PERSPECTIVE_FIRST_PERSON) if data is None else str(data)

    def _new_slider(self, parent: QWidget, min_value: int, max_value: int) -> WheelPassthroughSlider:
        slider = WheelPassthroughSlider(Qt.Orientation.Horizontal, parent)
        slider.setRange(int(min_value), int(max_value))
        return slider

    def _add_toggle(self, layout: QVBoxLayout, parent: QWidget, text: str, slot) -> BedrockToggleRow:
        row = BedrockToggleRow(str(text), parent)
        row.toggled.connect(slot)
        layout.addWidget(row)
        return row

    def _add_keybind_row(self, layout: QVBoxLayout, parent: QWidget, action: str) -> KeybindRow:
        row = KeybindRow(action_display_name(str(action)), parent)
        row.binding_changed.connect(lambda binding_text, action_id=str(action): self.keybind_changed.emit(str(action_id), str(binding_text)))
        row.clear_requested.connect(lambda action_id=str(action): self.keybind_changed.emit(str(action_id), ""))
        layout.addWidget(row)
        self._keybind_rows[str(action)] = row
        return row

    def _update_mode_toggle_text(self, creative_mode: bool) -> None:
        self._btn_mode_toggle.setText("Game Mode: Creative" if bool(creative_mode) else "Game Mode: Survival")

    def _on_mode_toggle_clicked(self, checked: bool) -> None:
        self._update_mode_toggle_text(bool(checked))
        self.creative_mode_changed.emit(bool(checked))

    def _set_tab(self, index: int) -> None:
        selected_index = int(max(0, min(3, int(index))))
        self._stack.setCurrentIndex(selected_index)
        current_page = self._stack.currentWidget()
        if isinstance(current_page, QScrollArea):
            current_page.verticalScrollBar().setValue(0)
            current_page.viewport().update()
            page_host = current_page.widget()
            if page_host is not None:
                page_host.update()
        self._stack.update()
        self._tab_video.setChecked(selected_index == 0)
        self._tab_controls.setChecked(selected_index == 1)
        self._tab_audio.setChecked(selected_index == 2)
        self._tab_game.setChecked(selected_index == 3)

    def sync_values(self, **kwargs) -> None:
        _sync_overlay_values(self, **kwargs)

    def _on_fov(self, value: int) -> None:
        self._lbl_fov.setText(f"FOV: {int(value)}")
        self.fov_changed.emit(float(value))

    def _on_sens(self, value: int) -> None:
        sensitivity = float(value) / float(self._params.sens_scale)
        self._lbl_sens.setText(f"Mouse sensitivity: {sensitivity:.3f} deg/px")
        self.sens_changed.emit(sensitivity)

    def _on_view_bobbing_toggled(self, on: bool) -> None:
        enabled = bool(on)
        self._sld_view_bobbing_strength.setEnabled(enabled)
        self.view_bobbing_changed.emit(enabled)

    def _on_camera_shake_toggled(self, on: bool) -> None:
        enabled = bool(on)
        self._sld_camera_shake_strength.setEnabled(enabled)
        self.camera_shake_changed.emit(enabled)

    def _update_cloud_controls_enabled(self, enabled: bool) -> None:
        self._sld_cloud_density.setEnabled(bool(enabled))
        self._sld_cloud_seed.setEnabled(bool(enabled))

    def _on_clouds_toggled(self, on: bool) -> None:
        enabled = bool(on)
        self._update_cloud_controls_enabled(enabled)
        self.clouds_enabled_changed.emit(enabled)

    def _on_view_bobbing_strength(self, value: int) -> None:
        percent = int(max(int(self._params.bob_strength_percent_min), min(int(self._params.bob_strength_percent_max), int(value))))
        self._lbl_view_bobbing_strength.setText(f"View Bobbing strength: {percent}%")
        self.view_bobbing_strength_changed.emit(float(percent) / 100.0)

    def _on_camera_shake_strength(self, value: int) -> None:
        percent = int(max(int(self._params.shake_strength_percent_min), min(int(self._params.shake_strength_percent_max), int(value))))
        self._lbl_camera_shake_strength.setText(f"Camera Shake strength: {percent}%")
        self.camera_shake_strength_changed.emit(float(percent) / 100.0)

    def _on_camera_perspective(self, _index: int) -> None:
        self.camera_perspective_changed.emit(str(self._current_camera_perspective_value()))

    def _on_rd(self, value: int) -> None:
        render_distance = int(value)
        self._lbl_rd.setText(f"Render distance: {render_distance} chunks")
        self.render_distance_changed.emit(int(render_distance))

    def _on_sun_az(self, value: int) -> None:
        self._lbl_sun_az.setText(f"Sun azimuth: {int(value)} deg")
        self.sun_azimuth_changed.emit(float(value))

    def _on_sun_el(self, value: int) -> None:
        self._lbl_sun_el.setText(f"Sun elevation: {int(value)} deg")
        self.sun_elevation_changed.emit(float(value))

    def _on_cloud_density(self, value: int) -> None:
        density = int(value)
        self._lbl_cloud_density.setText(f"Cloud density: {density}")
        self.cloud_density_changed.emit(int(density))

    def _on_cloud_seed(self, value: int) -> None:
        seed = int(value)
        self._lbl_cloud_seed.setText(f"Cloud seed: {seed}")
        self.cloud_seed_changed.emit(int(seed))

    def _on_cloud_flow_direction(self, _index: int) -> None:
        self.cloud_flow_direction_changed.emit(str(self._current_cloud_flow_value()))

    def _on_master_volume(self, value: int) -> None:
        percent = int(max(0, min(100, int(value))))
        self._lbl_master_volume.setText(f"Master volume: {percent}%")
        self.master_volume_changed.emit(float(percent) / 100.0)

    def _on_ambient_volume(self, value: int) -> None:
        percent = int(max(0, min(100, int(value))))
        self._lbl_ambient_volume.setText(f"Ambient volume: {percent}%")
        self.ambient_volume_changed.emit(float(percent) / 100.0)

    def _on_block_volume(self, value: int) -> None:
        percent = int(max(0, min(100, int(value))))
        self._lbl_block_volume.setText(f"Block volume: {percent}%")
        self.block_volume_changed.emit(float(percent) / 100.0)

    def _on_player_volume(self, value: int) -> None:
        percent = int(max(0, min(100, int(value))))
        self._lbl_player_volume.setText(f"Player volume: {percent}%")
        self.player_volume_changed.emit(float(percent) / 100.0)

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.back_requested.emit()
            return
        super().keyPressEvent(e)

    def closeEvent(self, event) -> None:
        if bool(self._as_window):
            event.ignore()
            self.back_requested.emit()
            return
        super().closeEvent(event)
