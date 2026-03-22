# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from ....application.runtime.keybinds import action_display_name
from ....application.runtime.state.camera_perspective import CAMERA_PERSPECTIVE_FIRST_PERSON
from ..config.pause_overlay_params import DEFAULT_PAUSE_OVERLAY_PARAMS, PauseOverlayParams
from ...opengl.runtime.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION
from ..common.settings_controls import BedrockToggleRow, KeybindRow, WheelPassthroughSlider
from .page_builders import build_audio_tab, build_controls_tab, build_game_tab, build_video_tab
from .value_sync import sync_overlay_values


class SettingsOverlay(QWidget):
    back_requested = pyqtSignal()
    fov_changed = pyqtSignal(float)
    sens_changed = pyqtSignal(float)
    invert_x_changed = pyqtSignal(bool)
    invert_y_changed = pyqtSignal(bool)
    fullscreen_changed = pyqtSignal(bool)
    hide_hud_changed = pyqtSignal(bool)
    hide_hand_changed = pyqtSignal(bool)
    crosshair_pixels_changed = pyqtSignal(object)
    crosshair_default_requested = pyqtSignal()
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

    def __init__(self, parent: QWidget | None=None, params: PauseOverlayParams=DEFAULT_PAUSE_OVERLAY_PARAMS) -> None:
        super().__init__(parent)
        self._params = params
        self._keybind_rows: dict[str, KeybindRow] = {}
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("settingsRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        panel.setMinimumWidth(960)
        panel.setMinimumHeight(620)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("SETTINGS", panel)
        title.setObjectName("title")
        title_row.addWidget(title)
        title_row.addStretch(1)

        btn_back = QPushButton("Back", panel)
        btn_back.setObjectName("menuBtn")
        btn_back.clicked.connect(self.back_requested.emit)
        title_row.addWidget(btn_back)
        panel_layout.addLayout(title_row)

        subtitle = QLabel("Video, Controls, Audio, and Game Player settings are available in separate tabs.", panel)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        panel_layout.addWidget(subtitle)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)
        self._tab_video = self._make_tab_button("Video", 0, panel)
        self._tab_controls = self._make_tab_button("Controls", 1, panel)
        self._tab_audio = self._make_tab_button("Audio", 2, panel)
        self._tab_game = self._make_tab_button("Game Player", 3, panel)
        tab_row.addWidget(self._tab_video)
        tab_row.addWidget(self._tab_controls)
        tab_row.addWidget(self._tab_audio)
        tab_row.addWidget(self._tab_game)
        tab_row.addStretch(1)
        panel_layout.addLayout(tab_row)

        self._stack = QStackedWidget(panel)
        panel_layout.addWidget(self._stack, stretch=1)

        build_video_tab(self)
        build_controls_tab(self)
        build_audio_tab(self)
        build_game_tab(self)
        self._set_tab(0)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def _make_tab_button(self, text: str, index: int, parent: QWidget) -> QPushButton:
        button = QPushButton(text, parent)
        button.setObjectName("tabBtn")
        button.setCheckable(True)
        button.setAutoExclusive(True)
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
    def _section(parent: QWidget, text: str) -> QLabel:
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
        self._tab_video.setChecked(selected_index == 0)
        self._tab_controls.setChecked(selected_index == 1)
        self._tab_audio.setChecked(selected_index == 2)
        self._tab_game.setChecked(selected_index == 3)

    def sync_values(self, **kwargs) -> None:
        sync_overlay_values(self, **kwargs)

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
