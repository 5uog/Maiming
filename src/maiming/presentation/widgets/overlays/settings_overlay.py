# FILE: src/maiming/presentation/widgets/overlays/settings_overlay.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QCheckBox,
    QFrame,
    QSizePolicy,
    QStackedWidget,
    QScrollArea,
)

from maiming.presentation.config.pause_overlay_params import (
    PauseOverlayParams,
    DEFAULT_PAUSE_OVERLAY_PARAMS,
)

class SettingsOverlay(QWidget):
    back_requested = pyqtSignal()

    fov_changed = pyqtSignal(float)
    sens_changed = pyqtSignal(float)
    invert_x_changed = pyqtSignal(bool)
    invert_y_changed = pyqtSignal(bool)

    outline_selection_changed = pyqtSignal(bool)

    cloud_wireframe_changed = pyqtSignal(bool)
    clouds_enabled_changed = pyqtSignal(bool)
    cloud_density_changed = pyqtSignal(int)
    cloud_seed_changed = pyqtSignal(int)

    world_wireframe_changed = pyqtSignal(bool)
    shadow_enabled_changed = pyqtSignal(bool)

    sun_azimuth_changed = pyqtSignal(float)
    sun_elevation_changed = pyqtSignal(float)

    build_mode_changed = pyqtSignal(bool)
    auto_jump_changed = pyqtSignal(bool)
    auto_sprint_changed = pyqtSignal(bool)

    render_distance_changed = pyqtSignal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        params: PauseOverlayParams = DEFAULT_PAUSE_OVERLAY_PARAMS,
    ) -> None:
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
        panel.setMinimumWidth(920)
        panel.setMinimumHeight(580)

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

        subtitle = QLabel(
            "Visual, Controls, and Game & Player (Advanced) now live in separate tabs.",
            panel,
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        pv.addWidget(subtitle)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self._tab_visual = self._make_tab_button("Visual", 0, panel)
        self._tab_controls = self._make_tab_button("Controls", 1, panel)
        self._tab_game = self._make_tab_button("Game & Player (Advanced)", 2, panel)

        tab_row.addWidget(self._tab_visual)
        tab_row.addWidget(self._tab_controls)
        tab_row.addWidget(self._tab_game)
        tab_row.addStretch(1)

        pv.addLayout(tab_row)

        self._stack = QStackedWidget(panel)
        pv.addWidget(self._stack, stretch=1)

        self._build_visual_tab()
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

    def _build_visual_tab(self) -> None:
        scroll, host, lay = self._make_scroll_page()

        lay.addWidget(self._section(host, "Camera"))

        fov_row = QVBoxLayout()
        self._lbl_fov = QLabel("FOV: 80", host)
        self._lbl_fov.setObjectName("valueLabel")
        self._sld_fov = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_fov.setRange(
            int(self._params.fov_min),
            int(self._params.fov_max),
        )
        self._sld_fov.valueChanged.connect(self._on_fov)
        fov_row.addWidget(self._lbl_fov)
        fov_row.addWidget(self._sld_fov)
        lay.addLayout(fov_row)

        lay.addWidget(self._sep(host))

        lay.addWidget(self._section(host, "World"))

        rd_row = QVBoxLayout()
        self._lbl_rd = QLabel("Render distance: 6 chunks", host)
        self._lbl_rd.setObjectName("valueLabel")
        self._sld_rd = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_rd.setRange(
            int(self._params.render_dist_min),
            int(self._params.render_dist_max),
        )
        self._sld_rd.valueChanged.connect(self._on_rd)
        rd_row.addWidget(self._lbl_rd)
        rd_row.addWidget(self._sld_rd)
        lay.addLayout(rd_row)

        world_toggle_row = QHBoxLayout()

        self._cb_outline_sel = QCheckBox("Outline selection", host)
        self._cb_outline_sel.toggled.connect(self.outline_selection_changed.emit)
        world_toggle_row.addWidget(self._cb_outline_sel)

        self._cb_world_wire = QCheckBox("World wireframe", host)
        self._cb_world_wire.toggled.connect(self.world_wireframe_changed.emit)
        world_toggle_row.addWidget(self._cb_world_wire)

        self._cb_shadow_enabled = QCheckBox("Enable shadow map", host)
        self._cb_shadow_enabled.toggled.connect(self.shadow_enabled_changed.emit)
        world_toggle_row.addWidget(self._cb_shadow_enabled)

        world_toggle_row.addStretch(1)
        lay.addLayout(world_toggle_row)

        lay.addWidget(self._sep(host))

        lay.addWidget(self._section(host, "Clouds"))

        clouds_toggle_row = QHBoxLayout()

        self._cb_clouds_enabled = QCheckBox("Show clouds", host)
        self._cb_clouds_enabled.toggled.connect(self.clouds_enabled_changed.emit)
        clouds_toggle_row.addWidget(self._cb_clouds_enabled)

        self._cb_cloud_wire = QCheckBox("Cloud wireframe", host)
        self._cb_cloud_wire.toggled.connect(self.cloud_wireframe_changed.emit)
        clouds_toggle_row.addWidget(self._cb_cloud_wire)

        clouds_toggle_row.addStretch(1)
        lay.addLayout(clouds_toggle_row)

        cloud_density_row = QVBoxLayout()
        self._lbl_cloud_density = QLabel("Cloud density: 1", host)
        self._lbl_cloud_density.setObjectName("valueLabel")
        self._sld_cloud_density = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_cloud_density.setRange(0, 4)
        self._sld_cloud_density.valueChanged.connect(self._on_cloud_density)
        cloud_density_row.addWidget(self._lbl_cloud_density)
        cloud_density_row.addWidget(self._sld_cloud_density)
        lay.addLayout(cloud_density_row)

        cloud_seed_row = QVBoxLayout()
        self._lbl_cloud_seed = QLabel("Cloud seed: 1337", host)
        self._lbl_cloud_seed.setObjectName("valueLabel")
        self._sld_cloud_seed = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_cloud_seed.setRange(0, 9999)
        self._sld_cloud_seed.valueChanged.connect(self._on_cloud_seed)
        cloud_seed_row.addWidget(self._lbl_cloud_seed)
        cloud_seed_row.addWidget(self._sld_cloud_seed)
        lay.addLayout(cloud_seed_row)

        lay.addWidget(self._sep(host))

        lay.addWidget(self._section(host, "Sun"))

        sun_az_row = QVBoxLayout()
        self._lbl_sun_az = QLabel("Sun azimuth: 45 deg", host)
        self._lbl_sun_az.setObjectName("valueLabel")
        self._sld_sun_az = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_sun_az.setRange(
            int(self._params.sun_az_min),
            int(self._params.sun_az_max),
        )
        self._sld_sun_az.valueChanged.connect(self._on_sun_az)
        sun_az_row.addWidget(self._lbl_sun_az)
        sun_az_row.addWidget(self._sld_sun_az)
        lay.addLayout(sun_az_row)

        sun_el_row = QVBoxLayout()
        self._lbl_sun_el = QLabel("Sun elevation: 60 deg", host)
        self._lbl_sun_el.setObjectName("valueLabel")
        self._sld_sun_el = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_sun_el.setRange(
            int(self._params.sun_el_min),
            int(self._params.sun_el_max),
        )
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
        self._sld_sens = QSlider(Qt.Orientation.Horizontal, host)
        self._sld_sens.setRange(
            int(self._params.sens_milli_min),
            int(self._params.sens_milli_max),
        )
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

        lay.addWidget(self._section(host, "Game & Player (Advanced)"))

        self._cb_build_mode = QCheckBox("Build mode", host)
        self._cb_build_mode.toggled.connect(self.build_mode_changed.emit)
        lay.addWidget(self._cb_build_mode)

        self._cb_auto_jump = QCheckBox("Auto-Jump (Bedrock-style)", host)
        self._cb_auto_jump.toggled.connect(self.auto_jump_changed.emit)
        lay.addWidget(self._cb_auto_jump)

        self._cb_auto_sprint = QCheckBox("Auto-Sprint (forward input)", host)
        self._cb_auto_sprint.toggled.connect(self.auto_sprint_changed.emit)
        lay.addWidget(self._cb_auto_sprint)

        lay.addStretch(1)
        self._stack.addWidget(scroll)

    def _set_tab(self, index: int) -> None:
        i = int(max(0, min(2, int(index))))
        self._stack.setCurrentIndex(i)

        self._tab_visual.setChecked(i == 0)
        self._tab_controls.setChecked(i == 1)
        self._tab_game.setChecked(i == 2)

    def sync_values(
        self,
        *,
        fov_deg: float,
        sens_deg_per_px: float,
        inv_x: bool,
        inv_y: bool,
        outline_selection: bool,
        cloud_wire: bool,
        clouds_enabled: bool,
        cloud_density: int,
        cloud_seed: int,
        world_wire: bool,
        shadow_enabled: bool,
        sun_az_deg: float,
        sun_el_deg: float,
        build_mode: bool,
        auto_jump_enabled: bool,
        auto_sprint_enabled: bool,
        render_distance_chunks: int,
    ) -> None:
        fov_i = int(round(float(fov_deg)))
        fov_i = max(int(self._params.fov_min), min(int(self._params.fov_max), fov_i))
        self._sld_fov.blockSignals(True)
        self._sld_fov.setValue(fov_i)
        self._sld_fov.blockSignals(False)
        self._lbl_fov.setText(f"FOV: {fov_i}")

        s = max(
            float(self._params.sens_min),
            min(float(self._params.sens_max), float(sens_deg_per_px)),
        )
        si = int(round(s * float(self._params.sens_scale)))
        si = max(int(self._params.sens_milli_min), min(int(self._params.sens_milli_max), si))
        self._sld_sens.blockSignals(True)
        self._sld_sens.setValue(si)
        self._sld_sens.blockSignals(False)
        self._lbl_sens.setText(f"Mouse sensitivity: {s:.3f} deg/px")

        rd = int(
            max(
                int(self._params.render_dist_min),
                min(int(self._params.render_dist_max), int(render_distance_chunks)),
            )
        )
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

        self._cb_outline_sel.blockSignals(True)
        self._cb_outline_sel.setChecked(bool(outline_selection))
        self._cb_outline_sel.blockSignals(False)

        self._cb_cloud_wire.blockSignals(True)
        self._cb_cloud_wire.setChecked(bool(cloud_wire))
        self._cb_cloud_wire.blockSignals(False)

        self._cb_world_wire.blockSignals(True)
        self._cb_world_wire.setChecked(bool(world_wire))
        self._cb_world_wire.blockSignals(False)

        self._cb_shadow_enabled.blockSignals(True)
        self._cb_shadow_enabled.setChecked(bool(shadow_enabled))
        self._cb_shadow_enabled.blockSignals(False)

        self._cb_clouds_enabled.blockSignals(True)
        self._cb_clouds_enabled.setChecked(bool(clouds_enabled))
        self._cb_clouds_enabled.blockSignals(False)

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

        self._cb_build_mode.blockSignals(True)
        self._cb_build_mode.setChecked(bool(build_mode))
        self._cb_build_mode.blockSignals(False)

        self._cb_auto_jump.blockSignals(True)
        self._cb_auto_jump.setChecked(bool(auto_jump_enabled))
        self._cb_auto_jump.blockSignals(False)

        self._cb_auto_sprint.blockSignals(True)
        self._cb_auto_sprint.setChecked(bool(auto_sprint_enabled))
        self._cb_auto_sprint.blockSignals(False)

    def _on_fov(self, v: int) -> None:
        self._lbl_fov.setText(f"FOV: {int(v)}")
        self.fov_changed.emit(float(v))

    def _on_sens(self, v: int) -> None:
        s = float(v) / float(self._params.sens_scale)
        self._lbl_sens.setText(f"Mouse sensitivity: {s:.3f} deg/px")
        self.sens_changed.emit(s)

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

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.back_requested.emit()
            return
        super().keyPressEvent(e)