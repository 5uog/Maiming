# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/settings/advanced_scalar_control.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ..common.settings_controls import WheelPassthroughDoubleSpinBox, WheelPassthroughSlider


class AdvancedScalarControl(QWidget):
    value_changed = pyqtSignal(float)

    def __init__(self, *, title: str, min_value: float, max_value: float, slider_scale: float, decimals: int, default_value: float, parent: QWidget | None=None) -> None:
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
        clamped = max(float(self._min), min(float(self._max), float(value)))
        return int(round(clamped * float(self._scale)))

    def set_value(self, value: float) -> None:
        clamped = max(float(self._min), min(float(self._max), float(value)))
        slider_value = self._value_to_slider(float(clamped))

        self._guard = True
        try:
            self._slider.setValue(int(slider_value))
            self._spin.setValue(float(clamped))
        finally:
            self._guard = False

        self._label.setText(f"{self._title}: {float(clamped):.{int(self._decimals)}f}")

    def reset_to_default(self) -> None:
        self.set_value(float(self._default))
        self.value_changed.emit(float(self._default))

    def _on_slider(self, slider_value: int) -> None:
        if bool(self._guard):
            return

        value = self._slider_to_value(int(slider_value))
        self._guard = True
        try:
            self._spin.setValue(float(value))
        finally:
            self._guard = False

        self._label.setText(f"{self._title}: {float(value):.{int(self._decimals)}f}")
        self.value_changed.emit(float(value))

    def _on_spin(self, spin_value: float) -> None:
        if bool(self._guard):
            return

        value = max(float(self._min), min(float(self._max), float(spin_value)))
        slider_value = self._value_to_slider(float(value))

        self._guard = True
        try:
            self._slider.setValue(int(slider_value))
        finally:
            self._guard = False

        self._label.setText(f"{self._title}: {float(value):.{int(self._decimals)}f}")
        self.value_changed.emit(float(value))
