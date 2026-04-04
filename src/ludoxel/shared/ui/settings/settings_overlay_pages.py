# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout

from ....application.runtime.keybinds import CONTROL_SECTION_GAMEPLAY, CONTROL_SECTION_MOVEMENT, HOTBAR_ACTIONS
from ....application.runtime.state.camera_perspective import CAMERA_PERSPECTIVE_LABELS, CAMERA_PERSPECTIVE_ORDER
from ....application.runtime.state.runtime_preferences import RuntimePreferences
from ..common.status_overlay import status_overlay_title_image_path
from ...world.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from .cloud_flow_options import CLOUD_FLOW_OPTIONS
from .widgets.advanced_scalar_control import AdvancedScalarControl
from .widgets.crosshair_widgets import CrosshairPixelEditor, CrosshairPreviewWidget

if TYPE_CHECKING:
    from .settings_overlay import SettingsOverlay


def build_video_tab(overlay: "SettingsOverlay") -> None:
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
    layout.addWidget(overlay._section(host, "Player Model"))

    overlay._ctl_arm_rotation_limit_min = AdvancedScalarControl(title="Arm rotation minimum", min_value=float(RuntimePreferences.ARM_ROTATION_LIMIT_ALLOWED_MIN_DEG), max_value=float(RuntimePreferences.ARM_ROTATION_LIMIT_ALLOWED_MAX_DEG), slider_scale=1.0, decimals=0, default_value=float(RuntimePreferences.DEFAULT_ARM_ROTATION_LIMIT_MIN_DEG), parent=host)
    overlay._ctl_arm_rotation_limit_min.value_changed.connect(overlay.arm_rotation_limit_min_changed.emit)
    layout.addWidget(overlay._ctl_arm_rotation_limit_min)

    overlay._ctl_arm_rotation_limit_max = AdvancedScalarControl(title="Arm rotation maximum", min_value=float(RuntimePreferences.ARM_ROTATION_LIMIT_ALLOWED_MIN_DEG), max_value=float(RuntimePreferences.ARM_ROTATION_LIMIT_ALLOWED_MAX_DEG), slider_scale=1.0, decimals=0, default_value=float(RuntimePreferences.DEFAULT_ARM_ROTATION_LIMIT_MAX_DEG), parent=host)
    overlay._ctl_arm_rotation_limit_max.value_changed.connect(overlay.arm_rotation_limit_max_changed.emit)
    layout.addWidget(overlay._ctl_arm_rotation_limit_max)

    overlay._ctl_arm_swing_duration = AdvancedScalarControl(title="Arm swing duration", min_value=float(RuntimePreferences.ARM_SWING_DURATION_MIN_S), max_value=float(RuntimePreferences.ARM_SWING_DURATION_MAX_S), slider_scale=100.0, decimals=2, default_value=float(RuntimePreferences.DEFAULT_ARM_SWING_DURATION_S), parent=host)
    overlay._ctl_arm_swing_duration.value_changed.connect(overlay.arm_swing_duration_changed.emit)
    layout.addWidget(overlay._ctl_arm_swing_duration)

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


def build_controls_tab(overlay: "SettingsOverlay") -> None:
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


def build_audio_tab(overlay: "SettingsOverlay") -> None:
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


def build_game_tab(overlay: "SettingsOverlay") -> None:
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
    layout.addWidget(overlay._section(host, "Player Identity"))

    overlay._name_edit = QLineEdit(host)
    overlay._name_edit.setPlaceholderText("Leave blank for a random name each launch")
    overlay._name_edit.editingFinished.connect(overlay._on_player_name_edited)
    layout.addWidget(overlay._name_edit)

    overlay._player_name_hint = QLabel("", host)
    overlay._player_name_hint.setObjectName("subtitle")
    overlay._player_name_hint.setWordWrap(True)
    layout.addWidget(overlay._player_name_hint)

    layout.addWidget(overlay._sep(host))
    layout.addWidget(overlay._section(host, "Interaction Parameters"))

    overlay._ctl_block_break_repeat_interval = AdvancedScalarControl(title="Break repeat interval", min_value=float(overlay._params.block_break_repeat_interval_milli_min) / float(overlay._params.block_break_repeat_interval_scale), max_value=float(overlay._params.block_break_repeat_interval_milli_max) / float(overlay._params.block_break_repeat_interval_scale), slider_scale=float(overlay._params.block_break_repeat_interval_scale), decimals=int(overlay._params.block_break_repeat_interval_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_BREAK_REPEAT_INTERVAL_S), parent=host)
    overlay._ctl_block_break_repeat_interval.value_changed.connect(overlay.block_break_repeat_interval_changed.emit)
    layout.addWidget(overlay._ctl_block_break_repeat_interval)

    overlay._ctl_block_place_repeat_interval = AdvancedScalarControl(title="Place repeat interval", min_value=float(overlay._params.block_place_repeat_interval_milli_min) / float(overlay._params.block_place_repeat_interval_scale), max_value=float(overlay._params.block_place_repeat_interval_milli_max) / float(overlay._params.block_place_repeat_interval_scale), slider_scale=float(overlay._params.block_place_repeat_interval_scale), decimals=int(overlay._params.block_place_repeat_interval_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_PLACE_REPEAT_INTERVAL_S), parent=host)
    overlay._ctl_block_place_repeat_interval.value_changed.connect(overlay.block_place_repeat_interval_changed.emit)
    layout.addWidget(overlay._ctl_block_place_repeat_interval)

    overlay._ctl_block_interact_repeat_interval = AdvancedScalarControl(title="Interact repeat interval", min_value=float(overlay._params.block_interact_repeat_interval_milli_min) / float(overlay._params.block_interact_repeat_interval_scale), max_value=float(overlay._params.block_interact_repeat_interval_milli_max) / float(overlay._params.block_interact_repeat_interval_scale), slider_scale=float(overlay._params.block_interact_repeat_interval_scale), decimals=int(overlay._params.block_interact_repeat_interval_decimals), default_value=float(RuntimePreferences.DEFAULT_BLOCK_INTERACT_REPEAT_INTERVAL_S), parent=host)
    overlay._ctl_block_interact_repeat_interval.value_changed.connect(overlay.block_interact_repeat_interval_changed.emit)
    layout.addWidget(overlay._ctl_block_interact_repeat_interval)

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


def build_about_tab(overlay: "SettingsOverlay") -> None:
    scroll, host, layout = overlay._make_scroll_page()

    image_label = QLabel(host)
    image_label.setObjectName("aboutImage")
    image_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
    image_label.setVisible(False)
    if overlay._resource_root is not None:
        image_path = status_overlay_title_image_path(overlay._resource_root)
        pixmap = QPixmap() if image_path is None else QPixmap(str(image_path))
        if not pixmap.isNull():
            image_label.setPixmap(pixmap.scaled(420, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            image_label.setVisible(True)
    layout.addWidget(image_label, alignment=Qt.AlignmentFlag.AlignHCenter)

    author_card = QFrame(host)
    author_card.setObjectName("aboutCard")
    author_layout = QVBoxLayout(author_card)
    author_layout.setContentsMargins(18, 18, 18, 18)
    author_layout.setSpacing(10)

    author_title = QLabel("Creator", author_card)
    author_title.setObjectName("sectionTitle")
    author_layout.addWidget(author_title)

    author_name = QLabel("5uog", author_card)
    author_name.setObjectName("aboutLead")
    author_layout.addWidget(author_name)

    author_summary = QLabel("Ludoxel is authored as a focused desktop sandbox for voxel rendering, interaction experiments, and an integrated Othello subsystem inside one persistent PyQt6 shell.", author_card)
    author_summary.setObjectName("subtitle")
    author_summary.setWordWrap(True)
    author_layout.addWidget(author_summary)

    layout.addWidget(author_card)

    details_card = QFrame(host)
    details_card.setObjectName("aboutCard")
    details_layout = QVBoxLayout(details_card)
    details_layout.setContentsMargins(18, 18, 18, 18)
    details_layout.setSpacing(10)

    details_title = QLabel("Project Overview", details_card)
    details_title.setObjectName("sectionTitle")
    details_layout.addWidget(details_title)

    details_body = QLabel("The current application combines a persistent voxel play space, an OpenGL 4.3 Core Profile renderer, and a separate Othello mode that shares the same runtime shell. The project emphasizes deterministic state persistence, inspectable rendering behavior, and feature work that stays close to implemented mechanics rather than mock interfaces.", details_card)
    details_body.setObjectName("subtitle")
    details_body.setWordWrap(True)
    details_layout.addWidget(details_body)

    details_body_2 = QLabel("The About page uses the bundled Ludoxel mark because the present repository does not ship a dedicated creator portrait asset. The surrounding application identity, packaging metadata, and in-app documentation are kept aligned with the live code path.", details_card)
    details_body_2.setObjectName("subtitle")
    details_body_2.setWordWrap(True)
    details_layout.addWidget(details_body_2)

    layout.addWidget(details_card)
    layout.addStretch(1)
    overlay._stack.addWidget(scroll)
