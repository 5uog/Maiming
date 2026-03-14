# FILE: src/maiming/presentation/widgets/overlays/settings_overlay.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from ....domain.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from ...config.pause_overlay_params import DEFAULT_PAUSE_OVERLAY_PARAMS, PauseOverlayParams
from ..common.settings_controls import BedrockToggleRow, WheelPassthroughDoubleSpinBox, WheelPassthroughSlider

_CLOUD_FLOW_DIRECTIONS: tuple[tuple[str, str], ...] = (("east_to_west", "East -> West"), ("west_to_east", "West -> East"), ("south_to_north", "South -> North"), ("north_to_south", "North -> South"))

class AdvancedScalarControl(QWidget):
    value_changed = pyqtSignal(float)

    def __init__(self, *, title: str, min_value: float, max_value: float, slider_scale: float, decimals: int, default_value: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._title = str(title)
        self._min = float(min_value)
        self._max = float(max_value)
        self._scale = float(max(1.0, slider_scale))
        self._decimals = int(max(0, decimals))
        self._default = float(default_value)
        self._guard = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self._label = QLabel(self._title, self)
        self._label.setObjectName("valueLabel")
        root.addWidget(self._label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self._slider = WheelPassthroughSlider(Qt.Orientation.Horizontal, self)
        self._slider.setRange(int(round(float(self._min) * float(self._scale))), int(round(float(self._max) * float(self._scale))))
        row.addWidget(self._slider, stretch=1)

        self._spin = WheelPassthroughDoubleSpinBox(self)
        self._spin.setDecimals(int(self._decimals))
        self._spin.setRange(float(self._min), float(self._max))
        self._spin.setSingleStep(max(10.0 ** (-int(self._decimals)), 1.0 / float(self._scale)))
        self._spin.setKeyboardTracking(False)
        self._spin.setMinimumWidth(110)
        row.addWidget(self._spin)

        self._btn_reset = QPushButton("Reset", self)
        self._btn_reset.setObjectName("menuBtn")
        self._btn_reset.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row.addWidget(self._btn_reset)

        root.addLayout(row)

        self._slider.valueChanged.connect(self._on_slider)
        self._spin.valueChanged.connect(self._on_spin)
        self._btn_reset.clicked.connect(self.reset_to_default)

        self.set_value(float(self._default))

    def _slider_to_value(self, slider_value: int) -> float:
        return float(slider_value) / float(self._scale)

    def _value_to_slider(self, value: float) -> int:
        v = max(float(self._min), min(float(self._max), float(value)))
        return int(round(v * float(self._scale)))

    def set_value(self, value: float) -> None:
        v = max(float(self._min), min(float(self._max), float(value)))
        sv = self._value_to_slider(float(v))

        self._guard = True
        try:
            self._slider.setValue(int(sv))
            self._spin.setValue(float(v))
        finally:
            self._guard = False

        self._label.setText(f"{self._title}: {float(v):.{int(self._decimals)}f}")

    def reset_to_default(self) -> None:
        self.set_value(float(self._default))
        self.value_changed.emit(float(self._default))

    def _on_slider(self, slider_value: int) -> None:
        if bool(self._guard):
            return

        v = self._slider_to_value(int(slider_value))
        self._guard = True
        try:
            self._spin.setValue(float(v))
        finally:
            self._guard = False

        self._label.setText(f"{self._title}: {float(v):.{int(self._decimals)}f}")
        self.value_changed.emit(float(v))

    def _on_spin(self, spin_value: float) -> None:
        if bool(self._guard):
            return

        v = max(float(self._min), min(float(self._max), float(spin_value)))
        sv = self._value_to_slider(float(v))

        self._guard = True
        try:
            self._slider.setValue(int(sv))
        finally:
            self._guard = False

        self._label.setText(f"{self._title}: {float(v):.{int(self._decimals)}f}")
        self.value_changed.emit(float(v))

class SettingsOverlay(QWidget):
    back_requested = pyqtSignal()

    fov_changed = pyqtSignal(float)
    sens_changed = pyqtSignal(float)
    invert_x_changed = pyqtSignal(bool)
    invert_y_changed = pyqtSignal(bool)
    fullscreen_changed = pyqtSignal(bool)
    hide_hud_changed = pyqtSignal(bool)
    hide_hand_changed = pyqtSignal(bool)
    view_bobbing_changed = pyqtSignal(bool)
    camera_shake_changed = pyqtSignal(bool)
    view_bobbing_strength_changed = pyqtSignal(float)
    camera_shake_strength_changed = pyqtSignal(float)

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

    def __init__(self, parent: QWidget | None = None, params: PauseOverlayParams = DEFAULT_PAUSE_OVERLAY_PARAMS) -> None:
        super().__init__(parent)
        self._params = params

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

        pv = QVBoxLayout(panel)
        pv.setContentsMargins(18, 16, 18, 16)
        pv.setSpacing(12)

        title_row = QHBoxLayout()

        title = QLabel("SETTINGS", panel)
        title.setObjectName("title")
        title_row.addWidget(title)

        title_row.addStretch(1)

        btn_back = QPushButton("Back", panel)
        btn_back.setObjectName("menuBtn")
        btn_back.clicked.connect(self.back_requested.emit)
        title_row.addWidget(btn_back)

        pv.addLayout(title_row)

        subtitle = QLabel("Video, Controls, and Game Player settings are available in separate tabs.", panel)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        pv.addWidget(subtitle)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self._tab_video = self._make_tab_button("Video", 0, panel)
        self._tab_controls = self._make_tab_button("Controls", 1, panel)
        self._tab_game = self._make_tab_button("Game Player", 2, panel)

        tab_row.addWidget(self._tab_video)
        tab_row.addWidget(self._tab_controls)
        tab_row.addWidget(self._tab_game)
        tab_row.addStretch(1)

        pv.addLayout(tab_row)

        self._stack = QStackedWidget(panel)
        pv.addWidget(self._stack, stretch=1)

        self._build_video_tab()
        self._build_controls_tab()
        self._build_game_tab()

        self._set_tab(0)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def _make_tab_button(self, text: str, index: int, parent: QWidget) -> QPushButton:
        btn = QPushButton(text, parent)
        btn.setObjectName("tabBtn")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.clicked.connect(lambda _checked=False, i=index: self._set_tab(i))
        return btn

    def _make_scroll_page(self) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        scroll = QScrollArea(self._stack)
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        host = QWidget(scroll)
        host.setObjectName("settingsPage")

        lay = QVBoxLayout(host)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)

        scroll.setWidget(host)
        return scroll, host, lay

    @staticmethod
    def _sep(parent: QWidget) -> QFrame:
        sep = QFrame(parent)
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        return sep

    @staticmethod
    def _section(parent: QWidget, text: str) -> QLabel:
        lbl = QLabel(text, parent)
        lbl.setObjectName("sectionTitle")
        return lbl

    @staticmethod
    def _cloud_flow_index_for_value(value: str) -> int:
        raw = str(value).strip().lower()
        for i, (v, _label) in enumerate(_CLOUD_FLOW_DIRECTIONS):
            if raw == str(v):
                return i
        return 1

    def _current_cloud_flow_value(self) -> str:
        data = self._cmb_cloud_flow.currentData()
        if data is None:
            return "west_to_east"
        return str(data)

    def _new_slider(self, parent: QWidget, min_value: int, max_value: int) -> WheelPassthroughSlider:
        slider = WheelPassthroughSlider(Qt.Orientation.Horizontal, parent)
        slider.setRange(int(min_value), int(max_value))
        return slider

    def _add_toggle(self, layout: QVBoxLayout, parent: QWidget, text: str, slot) -> BedrockToggleRow:
        row = BedrockToggleRow(str(text), parent)
        row.toggled.connect(slot)
        layout.addWidget(row)
        return row

    def _build_video_tab(self) -> None:
        scroll, host, lay = self._make_scroll_page()

        lay.addWidget(self._section(host, "Display"))
        self._tg_fullscreen = self._add_toggle(lay, host, "Fullscreen", self.fullscreen_changed.emit)
        self._tg_hide_hud = self._add_toggle(lay, host, "Hide HUD", self.hide_hud_changed.emit)
        self._tg_hide_hand = self._add_toggle(lay, host, "Hide Hand", self.hide_hand_changed.emit)
        self._tg_view_bobbing = self._add_toggle(lay, host, "View Bobbing", self._on_view_bobbing_toggled)

        bob_row = QVBoxLayout()
        self._lbl_view_bobbing_strength = QLabel("View Bobbing strength: 35%", host)
        self._lbl_view_bobbing_strength.setObjectName("valueLabel")
        self._sld_view_bobbing_strength = self._new_slider(host, int(self._params.bob_strength_percent_min), int(self._params.bob_strength_percent_max))
        self._sld_view_bobbing_strength.valueChanged.connect(self._on_view_bobbing_strength)
        bob_row.addWidget(self._lbl_view_bobbing_strength)
        bob_row.addWidget(self._sld_view_bobbing_strength)
        lay.addLayout(bob_row)

        self._tg_camera_shake = self._add_toggle(lay, host, "Camera Shake", self._on_camera_shake_toggled)

        shake_row = QVBoxLayout()
        self._lbl_camera_shake_strength = QLabel("Camera Shake strength: 20%", host)
        self._lbl_camera_shake_strength.setObjectName("valueLabel")
        self._sld_camera_shake_strength = self._new_slider(host, int(self._params.shake_strength_percent_min), int(self._params.shake_strength_percent_max))
        self._sld_camera_shake_strength.valueChanged.connect(self._on_camera_shake_strength)
        shake_row.addWidget(self._lbl_camera_shake_strength)
        shake_row.addWidget(self._sld_camera_shake_strength)
        lay.addLayout(shake_row)

        fov_row = QVBoxLayout()
        self._lbl_fov = QLabel("FOV: 80", host)
        self._lbl_fov.setObjectName("valueLabel")
        self._sld_fov = self._new_slider(host, int(self._params.fov_min), int(self._params.fov_max))
        self._sld_fov.valueChanged.connect(self._on_fov)
        fov_row.addWidget(self._lbl_fov)
        fov_row.addWidget(self._sld_fov)
        lay.addLayout(fov_row)

        lay.addWidget(self._sep(host))

        lay.addWidget(self._section(host, "World"))

        rd_row = QVBoxLayout()
        self._lbl_rd = QLabel("Render distance: 6 chunks", host)
        self._lbl_rd.setObjectName("valueLabel")
        self._sld_rd = self._new_slider(host, int(self._params.render_dist_min), int(self._params.render_dist_max))
        self._sld_rd.valueChanged.connect(self._on_rd)
        rd_row.addWidget(self._lbl_rd)
        rd_row.addWidget(self._sld_rd)
        lay.addLayout(rd_row)

        self._tg_outline_sel = self._add_toggle(lay, host, "Outline selection", self.outline_selection_changed.emit)
        self._tg_world_wire = self._add_toggle(lay, host, "World wireflame", self.world_wireframe_changed.emit)
        self._tg_shadow_enabled = self._add_toggle(lay, host, "Shadow map", self.shadow_enabled_changed.emit)

        lay.addWidget(self._sep(host))

        lay.addWidget(self._section(host, "Clouds"))

        self._tg_clouds_enabled = self._add_toggle(lay, host, "Show clouds", self.clouds_enabled_changed.emit)
        self._tg_cloud_wire = self._add_toggle(lay, host, "Cloud wireflame", self.cloud_wireframe_changed.emit)

        cloud_flow_row = QHBoxLayout()
        self._lbl_cloud_flow = QLabel("Cloud flow direction", host)
        self._lbl_cloud_flow.setObjectName("valueLabel")
        cloud_flow_row.addWidget(self._lbl_cloud_flow)

        self._cmb_cloud_flow = QComboBox(host)
        for value, label in _CLOUD_FLOW_DIRECTIONS:
            self._cmb_cloud_flow.addItem(str(label), userData=str(value))
        self._cmb_cloud_flow.currentIndexChanged.connect(self._on_cloud_flow_direction)
        cloud_flow_row.addWidget(self._cmb_cloud_flow)
        cloud_flow_row.addStretch(1)
        lay.addLayout(cloud_flow_row)

        cloud_density_row = QVBoxLayout()
        self._lbl_cloud_density = QLabel("Cloud density: 1", host)
        self._lbl_cloud_density.setObjectName("valueLabel")
        self._sld_cloud_density = self._new_slider(host, 0, 4)
        self._sld_cloud_density.valueChanged.connect(self._on_cloud_density)
        cloud_density_row.addWidget(self._lbl_cloud_density)
        cloud_density_row.addWidget(self._sld_cloud_density)
        lay.addLayout(cloud_density_row)

        cloud_seed_row = QVBoxLayout()
        self._lbl_cloud_seed = QLabel("Cloud seed: 1337", host)
        self._lbl_cloud_seed.setObjectName("valueLabel")
        self._sld_cloud_seed = self._new_slider(host, 0, 9999)
        self._sld_cloud_seed.valueChanged.connect(self._on_cloud_seed)
        cloud_seed_row.addWidget(self._lbl_cloud_seed)
        cloud_seed_row.addWidget(self._sld_cloud_seed)
        lay.addLayout(cloud_seed_row)

        lay.addWidget(self._sep(host))

        lay.addWidget(self._section(host, "Sun"))

        sun_az_row = QVBoxLayout()
        self._lbl_sun_az = QLabel("Sun azimuth: 45 deg", host)
        self._lbl_sun_az.setObjectName("valueLabel")
        self._sld_sun_az = self._new_slider(host, int(self._params.sun_az_min), int(self._params.sun_az_max))
        self._sld_sun_az.valueChanged.connect(self._on_sun_az)
        sun_az_row.addWidget(self._lbl_sun_az)
        sun_az_row.addWidget(self._sld_sun_az)
        lay.addLayout(sun_az_row)

        sun_el_row = QVBoxLayout()
        self._lbl_sun_el = QLabel("Sun elevation: 60 deg", host)
        self._lbl_sun_el.setObjectName("valueLabel")
        self._sld_sun_el = self._new_slider(host, int(self._params.sun_el_min), int(self._params.sun_el_max))
        self._sld_sun_el.valueChanged.connect(self._on_sun_el)
        sun_el_row.addWidget(self._lbl_sun_el)
        sun_el_row.addWidget(self._sld_sun_el)
        lay.addLayout(sun_el_row)

        lay.addStretch(1)
        self._stack.addWidget(scroll)

    def _build_controls_tab(self) -> None:
        scroll, host, lay = self._make_scroll_page()

        lay.addWidget(self._section(host, "Mouse"))

        sens_row = QVBoxLayout()
        self._lbl_sens = QLabel("Mouse sensitivity: 0.090 deg/px", host)
        self._lbl_sens.setObjectName("valueLabel")
        self._sld_sens = self._new_slider(host, int(self._params.sens_milli_min), int(self._params.sens_milli_max))
        self._sld_sens.valueChanged.connect(self._on_sens)
        sens_row.addWidget(self._lbl_sens)
        sens_row.addWidget(self._sld_sens)
        lay.addLayout(sens_row)

        inv_row = QHBoxLayout()
        self._cb_inv_x = QCheckBox("Invert X", host)
        self._cb_inv_y = QCheckBox("Invert Y", host)
        self._cb_inv_x.toggled.connect(self.invert_x_changed.emit)
        self._cb_inv_y.toggled.connect(self.invert_y_changed.emit)
        inv_row.addWidget(self._cb_inv_x)
        inv_row.addWidget(self._cb_inv_y)
        inv_row.addStretch(1)
        lay.addLayout(inv_row)

        lay.addStretch(1)
        self._stack.addWidget(scroll)

    def _build_game_tab(self) -> None:
        scroll, host, lay = self._make_scroll_page()

        lay.addWidget(self._section(host, "Game Mode"))

        self._btn_mode_toggle = QPushButton(host)
        self._btn_mode_toggle.setObjectName("modeToggle")
        self._btn_mode_toggle.setCheckable(True)
        self._btn_mode_toggle.clicked.connect(self._on_mode_toggle_clicked)
        lay.addWidget(self._btn_mode_toggle)

        lay.addWidget(self._sep(host))
        lay.addWidget(self._section(host, "Player Options"))

        self._tg_auto_jump = self._add_toggle(lay, host, "Auto-Jump", self.auto_jump_changed.emit)
        self._tg_auto_sprint = self._add_toggle(lay, host, "Auto-Sprint", self.auto_sprint_changed.emit)

        lay.addWidget(self._sep(host))
        lay.addWidget(self._section(host, "Movement Parameters"))

        self._ctl_gravity = AdvancedScalarControl(title="Gravity", min_value=float(self._params.gravity_milli_min) / float(self._params.gravity_scale), max_value=float(self._params.gravity_milli_max) / float(self._params.gravity_scale), slider_scale=float(self._params.gravity_scale), decimals=int(self._params.gravity_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.gravity), parent=host)
        self._ctl_gravity.value_changed.connect(self.gravity_changed.emit)
        lay.addWidget(self._ctl_gravity)

        self._ctl_walk_speed = AdvancedScalarControl(title="Walk speed", min_value=float(self._params.walk_speed_milli_min) / float(self._params.walk_speed_scale), max_value=float(self._params.walk_speed_milli_max) / float(self._params.walk_speed_scale), slider_scale=float(self._params.walk_speed_scale), decimals=int(self._params.walk_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.walk_speed), parent=host)
        self._ctl_walk_speed.value_changed.connect(self.walk_speed_changed.emit)
        lay.addWidget(self._ctl_walk_speed)

        self._ctl_sprint_speed = AdvancedScalarControl(title="Sprint speed", min_value=float(self._params.sprint_speed_milli_min) / float(self._params.sprint_speed_scale), max_value=float(self._params.sprint_speed_milli_max) / float(self._params.sprint_speed_scale), slider_scale=float(self._params.sprint_speed_scale), decimals=int(self._params.sprint_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.sprint_speed), parent=host)
        self._ctl_sprint_speed.value_changed.connect(self.sprint_speed_changed.emit)
        lay.addWidget(self._ctl_sprint_speed)

        self._ctl_jump_v0 = AdvancedScalarControl(title="Jump velocity", min_value=float(self._params.jump_v0_milli_min) / float(self._params.jump_v0_scale), max_value=float(self._params.jump_v0_milli_max) / float(self._params.jump_v0_scale), slider_scale=float(self._params.jump_v0_scale), decimals=int(self._params.jump_v0_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.jump_v0), parent=host)
        self._ctl_jump_v0.value_changed.connect(self.jump_v0_changed.emit)
        lay.addWidget(self._ctl_jump_v0)

        self._ctl_auto_jump_cooldown = AdvancedScalarControl(title="Auto-jump cooldown", min_value=float(self._params.auto_jump_cooldown_milli_min) / float(self._params.auto_jump_cooldown_scale), max_value=float(self._params.auto_jump_cooldown_milli_max) / float(self._params.auto_jump_cooldown_scale), slider_scale=float(self._params.auto_jump_cooldown_scale), decimals=int(self._params.auto_jump_cooldown_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s), parent=host)
        self._ctl_auto_jump_cooldown.value_changed.connect(self.auto_jump_cooldown_changed.emit)
        lay.addWidget(self._ctl_auto_jump_cooldown)

        lay.addWidget(self._sep(host))
        lay.addWidget(self._section(host, "Flight Parameters"))

        self._ctl_fly_speed = AdvancedScalarControl(title="Flight speed", min_value=float(self._params.fly_speed_milli_min) / float(self._params.fly_speed_scale), max_value=float(self._params.fly_speed_milli_max) / float(self._params.fly_speed_scale), slider_scale=float(self._params.fly_speed_scale), decimals=int(self._params.fly_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.fly_speed), parent=host)
        self._ctl_fly_speed.value_changed.connect(self.fly_speed_changed.emit)
        lay.addWidget(self._ctl_fly_speed)

        self._ctl_fly_ascend_speed = AdvancedScalarControl(title="Ascend speed", min_value=float(self._params.fly_ascend_speed_milli_min) / float(self._params.fly_ascend_speed_scale), max_value=float(self._params.fly_ascend_speed_milli_max) / float(self._params.fly_ascend_speed_scale), slider_scale=float(self._params.fly_ascend_speed_scale), decimals=int(self._params.fly_ascend_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed), parent=host)
        self._ctl_fly_ascend_speed.value_changed.connect(self.fly_ascend_speed_changed.emit)
        lay.addWidget(self._ctl_fly_ascend_speed)

        self._ctl_fly_descend_speed = AdvancedScalarControl(title="Descend speed", min_value=float(self._params.fly_descend_speed_milli_min) / float(self._params.fly_descend_speed_scale), max_value=float(self._params.fly_descend_speed_milli_max) / float(self._params.fly_descend_speed_scale), slider_scale=float(self._params.fly_descend_speed_scale), decimals=int(self._params.fly_descend_speed_decimals), default_value=float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed), parent=host)
        self._ctl_fly_descend_speed.value_changed.connect(self.fly_descend_speed_changed.emit)
        lay.addWidget(self._ctl_fly_descend_speed)

        row_reset = QHBoxLayout()
        row_reset.addStretch(1)

        btn_reset_adv = QPushButton("Reset Advanced to Defaults", host)
        btn_reset_adv.setObjectName("menuBtn")
        btn_reset_adv.clicked.connect(self.advanced_reset_requested.emit)
        row_reset.addWidget(btn_reset_adv)

        lay.addLayout(row_reset)

        lay.addStretch(1)
        self._stack.addWidget(scroll)

    def _update_mode_toggle_text(self, creative_mode: bool) -> None:
        if bool(creative_mode):
            self._btn_mode_toggle.setText("Game Mode: Creative")
            return
        self._btn_mode_toggle.setText("Game Mode: Survival")

    def _on_mode_toggle_clicked(self, checked: bool) -> None:
        self._update_mode_toggle_text(bool(checked))
        self.creative_mode_changed.emit(bool(checked))

    def _set_tab(self, index: int) -> None:
        i = int(max(0, min(2, int(index))))
        self._stack.setCurrentIndex(i)

        self._tab_video.setChecked(i == 0)
        self._tab_controls.setChecked(i == 1)
        self._tab_game.setChecked(i == 2)

    @staticmethod
    def _sync_toggle(row: BedrockToggleRow, checked: bool) -> None:
        row.sync_checked(bool(checked))

    def sync_values(self, *, fov_deg: float, sens_deg_per_px: float, inv_x: bool, inv_y: bool, fullscreen: bool, hide_hud: bool, hide_hand: bool, view_bobbing_enabled: bool, camera_shake_enabled: bool, view_bobbing_strength: float, camera_shake_strength: float, outline_selection: bool, cloud_wire: bool, clouds_enabled: bool, cloud_density: int, cloud_seed: int, cloud_flow_direction: str, world_wire: bool, shadow_enabled: bool, sun_az_deg: float, sun_el_deg: float, creative_mode: bool, auto_jump_enabled: bool, auto_sprint_enabled: bool, gravity: float, walk_speed: float, sprint_speed: float, jump_v0: float, auto_jump_cooldown_s: float, fly_speed: float, fly_ascend_speed: float, fly_descend_speed: float, render_distance_chunks: int) -> None:
        fov_i = int(round(float(fov_deg)))
        fov_i = max(int(self._params.fov_min), min(int(self._params.fov_max), fov_i))
        self._sld_fov.blockSignals(True)
        self._sld_fov.setValue(fov_i)
        self._sld_fov.blockSignals(False)
        self._lbl_fov.setText(f"FOV: {fov_i}")

        s = max(float(self._params.sens_min), min(float(self._params.sens_max), float(sens_deg_per_px)))
        si = int(round(s * float(self._params.sens_scale)))
        si = max(int(self._params.sens_milli_min), min(int(self._params.sens_milli_max), si))
        self._sld_sens.blockSignals(True)
        self._sld_sens.setValue(si)
        self._sld_sens.blockSignals(False)
        self._lbl_sens.setText(f"Mouse sensitivity: {s:.3f} deg/px")

        rd = int(max(int(self._params.render_dist_min), min(int(self._params.render_dist_max), int(render_distance_chunks))))
        self._sld_rd.blockSignals(True)
        self._sld_rd.setValue(rd)
        self._sld_rd.blockSignals(False)
        self._lbl_rd.setText(f"Render distance: {rd} chunks")

        az = float(sun_az_deg) % 360.0
        az_i = int(round(az))
        az_i = max(int(self._params.sun_az_min), min(int(self._params.sun_az_max), az_i))
        self._sld_sun_az.blockSignals(True)
        self._sld_sun_az.setValue(az_i)
        self._sld_sun_az.blockSignals(False)
        self._lbl_sun_az.setText(f"Sun azimuth: {az_i} deg")

        el = float(sun_el_deg)
        el_i = int(round(el))
        el_i = max(int(self._params.sun_el_min), min(int(self._params.sun_el_max), el_i))
        self._sld_sun_el.blockSignals(True)
        self._sld_sun_el.setValue(el_i)
        self._sld_sun_el.blockSignals(False)
        self._lbl_sun_el.setText(f"Sun elevation: {el_i} deg")

        self._cb_inv_x.blockSignals(True)
        self._cb_inv_y.blockSignals(True)
        self._cb_inv_x.setChecked(bool(inv_x))
        self._cb_inv_y.setChecked(bool(inv_y))
        self._cb_inv_x.blockSignals(False)
        self._cb_inv_y.blockSignals(False)

        self._sync_toggle(self._tg_fullscreen, bool(fullscreen))
        self._sync_toggle(self._tg_hide_hud, bool(hide_hud))
        self._sync_toggle(self._tg_hide_hand, bool(hide_hand))
        self._sync_toggle(self._tg_view_bobbing, bool(view_bobbing_enabled))
        self._sync_toggle(self._tg_camera_shake, bool(camera_shake_enabled))

        vb_percent = int(round(max(0.0, min(1.0, float(view_bobbing_strength))) * 100.0))
        self._sld_view_bobbing_strength.blockSignals(True)
        self._sld_view_bobbing_strength.setValue(vb_percent)
        self._sld_view_bobbing_strength.blockSignals(False)
        self._lbl_view_bobbing_strength.setText(f"View Bobbing strength: {vb_percent}%")
        self._sld_view_bobbing_strength.setEnabled(bool(view_bobbing_enabled))

        cs_percent = int(round(max(0.0, min(1.0, float(camera_shake_strength))) * 100.0))
        self._sld_camera_shake_strength.blockSignals(True)
        self._sld_camera_shake_strength.setValue(cs_percent)
        self._sld_camera_shake_strength.blockSignals(False)
        self._lbl_camera_shake_strength.setText(f"Camera Shake strength: {cs_percent}%")
        self._sld_camera_shake_strength.setEnabled(bool(camera_shake_enabled))

        self._sync_toggle(self._tg_outline_sel, bool(outline_selection))
        self._sync_toggle(self._tg_world_wire, bool(world_wire))
        self._sync_toggle(self._tg_shadow_enabled, bool(shadow_enabled))
        self._sync_toggle(self._tg_clouds_enabled, bool(clouds_enabled))
        self._sync_toggle(self._tg_cloud_wire, bool(cloud_wire))

        idx = self._cloud_flow_index_for_value(str(cloud_flow_direction))
        self._cmb_cloud_flow.blockSignals(True)
        self._cmb_cloud_flow.setCurrentIndex(int(idx))
        self._cmb_cloud_flow.blockSignals(False)

        cd = int(max(0, min(4, int(cloud_density))))
        self._sld_cloud_density.blockSignals(True)
        self._sld_cloud_density.setValue(cd)
        self._sld_cloud_density.blockSignals(False)
        self._lbl_cloud_density.setText(f"Cloud density: {cd}")

        cs = int(max(0, min(9999, int(cloud_seed))))
        self._sld_cloud_seed.blockSignals(True)
        self._sld_cloud_seed.setValue(cs)
        self._sld_cloud_seed.blockSignals(False)
        self._lbl_cloud_seed.setText(f"Cloud seed: {cs}")

        self._btn_mode_toggle.blockSignals(True)
        self._btn_mode_toggle.setChecked(bool(creative_mode))
        self._btn_mode_toggle.blockSignals(False)
        self._update_mode_toggle_text(bool(creative_mode))

        self._sync_toggle(self._tg_auto_jump, bool(auto_jump_enabled))
        self._sync_toggle(self._tg_auto_sprint, bool(auto_sprint_enabled))

        self._ctl_gravity.set_value(float(gravity))
        self._ctl_walk_speed.set_value(float(walk_speed))
        self._ctl_sprint_speed.set_value(float(sprint_speed))
        self._ctl_jump_v0.set_value(float(jump_v0))
        self._ctl_auto_jump_cooldown.set_value(float(auto_jump_cooldown_s))
        self._ctl_fly_speed.set_value(float(fly_speed))
        self._ctl_fly_ascend_speed.set_value(float(fly_ascend_speed))
        self._ctl_fly_descend_speed.set_value(float(fly_descend_speed))

    def _on_fov(self, v: int) -> None:
        self._lbl_fov.setText(f"FOV: {int(v)}")
        self.fov_changed.emit(float(v))

    def _on_sens(self, v: int) -> None:
        s = float(v) / float(self._params.sens_scale)
        self._lbl_sens.setText(f"Mouse sensitivity: {s:.3f} deg/px")
        self.sens_changed.emit(s)

    def _on_view_bobbing_toggled(self, on: bool) -> None:
        enabled = bool(on)
        self._sld_view_bobbing_strength.setEnabled(enabled)
        self.view_bobbing_changed.emit(enabled)

    def _on_camera_shake_toggled(self, on: bool) -> None:
        enabled = bool(on)
        self._sld_camera_shake_strength.setEnabled(enabled)
        self.camera_shake_changed.emit(enabled)

    def _on_view_bobbing_strength(self, v: int) -> None:
        percent = int(max(int(self._params.bob_strength_percent_min), min(int(self._params.bob_strength_percent_max), int(v))))
        self._lbl_view_bobbing_strength.setText(f"View Bobbing strength: {percent}%")
        self.view_bobbing_strength_changed.emit(float(percent) / 100.0)

    def _on_camera_shake_strength(self, v: int) -> None:
        percent = int(max(int(self._params.shake_strength_percent_min), min(int(self._params.shake_strength_percent_max), int(v))))
        self._lbl_camera_shake_strength.setText(f"Camera Shake strength: {percent}%")
        self.camera_shake_strength_changed.emit(float(percent) / 100.0)

    def _on_rd(self, v: int) -> None:
        rv = int(v)
        self._lbl_rd.setText(f"Render distance: {rv} chunks")
        self.render_distance_changed.emit(int(rv))

    def _on_sun_az(self, v: int) -> None:
        self._lbl_sun_az.setText(f"Sun azimuth: {int(v)} deg")
        self.sun_azimuth_changed.emit(float(v))

    def _on_sun_el(self, v: int) -> None:
        self._lbl_sun_el.setText(f"Sun elevation: {int(v)} deg")
        self.sun_elevation_changed.emit(float(v))

    def _on_cloud_density(self, v: int) -> None:
        dv = int(v)
        self._lbl_cloud_density.setText(f"Cloud density: {dv}")
        self.cloud_density_changed.emit(int(dv))

    def _on_cloud_seed(self, v: int) -> None:
        sv = int(v)
        self._lbl_cloud_seed.setText(f"Cloud seed: {sv}")
        self.cloud_seed_changed.emit(int(sv))

    def _on_cloud_flow_direction(self, _index: int) -> None:
        self.cloud_flow_direction_changed.emit(str(self._current_cloud_flow_value()))

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.back_requested.emit()
            return
        super().keyPressEvent(e)