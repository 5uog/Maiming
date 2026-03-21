# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ....application.runtime.keybinds import CONTROL_SECTION_GAMEPLAY, CONTROL_SECTION_MOVEMENT, HOTBAR_ACTIONS
from ...world.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from .cloud_flow_options import CLOUD_FLOW_OPTIONS
from .advanced_scalar_control import AdvancedScalarControl

def build_video_tab(overlay) -> None:
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
    layout.addWidget(overlay._section(host, "Clouds"))

    overlay._tg_clouds_enabled = overlay._add_toggle(layout, host, "Show clouds", overlay.clouds_enabled_changed.emit)
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

def build_controls_tab(overlay) -> None:
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

def build_audio_tab(overlay) -> None:
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

def build_game_tab(overlay) -> None:
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

    layout.addWidget(overlay._sep(host))
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

    row_reset = QHBoxLayout()
    row_reset.addStretch(1)
    btn_reset_adv = QPushButton("Reset Advanced to Defaults", host)
    btn_reset_adv.setObjectName("menuBtn")
    btn_reset_adv.clicked.connect(overlay.advanced_reset_requested.emit)
    row_reset.addWidget(btn_reset_adv)
    layout.addLayout(row_reset)

    layout.addStretch(1)
    overlay._stack.addWidget(scroll)