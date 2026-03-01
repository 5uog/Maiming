# FILE: src/maiming/presentation/widgets/overlays/pause_overlay.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QCheckBox, QFrame, QSizePolicy
)

from maiming.presentation.config.pause_overlay_params import PauseOverlayParams, DEFAULT_PAUSE_OVERLAY_PARAMS

class PauseOverlay(QWidget):
    resume_requested = pyqtSignal()
    fov_changed = pyqtSignal(float)
    sens_changed = pyqtSignal(float)
    invert_x_changed = pyqtSignal(bool)
    invert_y_changed = pyqtSignal(bool)

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

    def __init__(self, parent: QWidget | None = None, params: PauseOverlayParams = DEFAULT_PAUSE_OVERLAY_PARAMS) -> None:
        super().__init__(parent)
        self._params = params

        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("pauseRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        panel.setMinimumWidth(560)

        pv = QVBoxLayout(panel)
        pv.setContentsMargins(18, 16, 18, 16)
        pv.setSpacing(12)

        title = QLabel("PAUSED", panel)
        title.setObjectName("title")
        pv.addWidget(title)

        btn_row = QHBoxLayout()
        self._btn_resume = QPushButton("Resume", panel)
        self._btn_resume.clicked.connect(self.resume_requested.emit)
        btn_row.addWidget(self._btn_resume)
        btn_row.addStretch(1)
        pv.addLayout(btn_row)

        sep = QFrame(panel)
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        pv.addWidget(sep)

        st = QLabel("Settings (MVP)", panel)
        st.setObjectName("sectionTitle")
        pv.addWidget(st)

        fov_row = QVBoxLayout()
        self._lbl_fov = QLabel("FOV: 80", panel)
        self._sld_fov = QSlider(Qt.Orientation.Horizontal, panel)
        self._sld_fov.setRange(int(self._params.fov_min), int(self._params.fov_max))
        self._sld_fov.valueChanged.connect(self._on_fov)
        fov_row.addWidget(self._lbl_fov)
        fov_row.addWidget(self._sld_fov)
        pv.addLayout(fov_row)

        sens_row = QVBoxLayout()
        self._lbl_sens = QLabel("Mouse sensitivity: 0.090 deg/px", panel)
        self._sld_sens = QSlider(Qt.Orientation.Horizontal, panel)
        self._sld_sens.setRange(int(self._params.sens_milli_min), int(self._params.sens_milli_max))
        self._sld_sens.valueChanged.connect(self._on_sens)
        sens_row.addWidget(self._lbl_sens)
        sens_row.addWidget(self._sld_sens)
        pv.addLayout(sens_row)

        sun_az_row = QVBoxLayout()
        self._lbl_sun_az = QLabel("Sun azimuth: 45 deg", panel)
        self._sld_sun_az = QSlider(Qt.Orientation.Horizontal, panel)
        self._sld_sun_az.setRange(int(self._params.sun_az_min), int(self._params.sun_az_max))
        self._sld_sun_az.valueChanged.connect(self._on_sun_az)
        sun_az_row.addWidget(self._lbl_sun_az)
        sun_az_row.addWidget(self._sld_sun_az)
        pv.addLayout(sun_az_row)

        sun_el_row = QVBoxLayout()
        self._lbl_sun_el = QLabel("Sun elevation: 60 deg", panel)
        self._sld_sun_el = QSlider(Qt.Orientation.Horizontal, panel)
        self._sld_sun_el.setRange(int(self._params.sun_el_min), int(self._params.sun_el_max))
        self._sld_sun_el.valueChanged.connect(self._on_sun_el)
        sun_el_row.addWidget(self._lbl_sun_el)
        sun_el_row.addWidget(self._sld_sun_el)
        pv.addLayout(sun_el_row)

        inv_row = QHBoxLayout()
        self._cb_inv_x = QCheckBox("Invert X", panel)
        self._cb_inv_y = QCheckBox("Invert Y", panel)
        self._cb_inv_x.toggled.connect(self.invert_x_changed.emit)
        self._cb_inv_y.toggled.connect(self.invert_y_changed.emit)
        inv_row.addWidget(self._cb_inv_x)
        inv_row.addWidget(self._cb_inv_y)
        inv_row.addStretch(1)
        pv.addLayout(inv_row)

        dbg_row = QHBoxLayout()
        self._cb_cloud_wire = QCheckBox("Cloud wireframe", panel)
        self._cb_world_wire = QCheckBox("World wireframe", panel)
        self._cb_cloud_wire.toggled.connect(self.cloud_wireframe_changed.emit)
        self._cb_world_wire.toggled.connect(self.world_wireframe_changed.emit)
        dbg_row.addWidget(self._cb_cloud_wire)
        dbg_row.addWidget(self._cb_world_wire)
        dbg_row.addStretch(1)
        pv.addLayout(dbg_row)

        shadow_row = QHBoxLayout()
        self._cb_shadow_enabled = QCheckBox("Enable shadow map", panel)
        self._cb_shadow_enabled.toggled.connect(self.shadow_enabled_changed.emit)
        shadow_row.addWidget(self._cb_shadow_enabled)
        shadow_row.addStretch(1)
        pv.addLayout(shadow_row)

        clouds_row = QHBoxLayout()
        self._cb_clouds_enabled = QCheckBox("Show clouds", panel)
        self._cb_clouds_enabled.toggled.connect(self.clouds_enabled_changed.emit)
        clouds_row.addWidget(self._cb_clouds_enabled)
        clouds_row.addStretch(1)
        pv.addLayout(clouds_row)

        cloud_density_row = QVBoxLayout()
        self._lbl_cloud_density = QLabel("Cloud density: 1", panel)
        self._sld_cloud_density = QSlider(Qt.Orientation.Horizontal, panel)
        self._sld_cloud_density.setRange(0, 4)
        self._sld_cloud_density.valueChanged.connect(self._on_cloud_density)
        cloud_density_row.addWidget(self._lbl_cloud_density)
        cloud_density_row.addWidget(self._sld_cloud_density)
        pv.addLayout(cloud_density_row)

        cloud_seed_row = QVBoxLayout()
        self._lbl_cloud_seed = QLabel("Cloud seed: 1337", panel)
        self._sld_cloud_seed = QSlider(Qt.Orientation.Horizontal, panel)
        self._sld_cloud_seed.setRange(0, 9999)
        self._sld_cloud_seed.valueChanged.connect(self._on_cloud_seed)
        cloud_seed_row.addWidget(self._lbl_cloud_seed)
        cloud_seed_row.addWidget(self._sld_cloud_seed)
        pv.addLayout(cloud_seed_row)

        build_row = QHBoxLayout()
        self._cb_build_mode = QCheckBox("Build mode", panel)
        self._cb_build_mode.toggled.connect(self.build_mode_changed.emit)
        build_row.addWidget(self._cb_build_mode)
        build_row.addStretch(1)
        pv.addLayout(build_row)

        aj_row = QHBoxLayout()
        self._cb_auto_jump = QCheckBox("Auto-Jump (Bedrock-style)", panel)
        self._cb_auto_jump.toggled.connect(self.auto_jump_changed.emit)
        aj_row.addWidget(self._cb_auto_jump)
        aj_row.addStretch(1)
        pv.addLayout(aj_row)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def sync_values(
        self,
        *,
        fov_deg: float,
        sens_deg_per_px: float,
        inv_x: bool,
        inv_y: bool,
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
    ) -> None:
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

    def _on_fov(self, v: int) -> None:
        self._lbl_fov.setText(f"FOV: {int(v)}")
        self.fov_changed.emit(float(v))

    def _on_sens(self, v: int) -> None:
        s = float(v) / float(self._params.sens_scale)
        self._lbl_sens.setText(f"Mouse sensitivity: {s:.3f} deg/px")
        self.sens_changed.emit(s)

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