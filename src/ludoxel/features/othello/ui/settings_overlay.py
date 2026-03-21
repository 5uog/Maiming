# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ..domain.game.types import OTHELLO_DIFFICULTY_INSANE, OTHELLO_DIFFICULTY_MEDIUM, OTHELLO_DIFFICULTY_STRONG, OTHELLO_DIFFICULTY_WEAK, OTHELLO_TIME_CONTROL_NONE, OTHELLO_TIME_CONTROL_PER_SIDE_20M, SIDE_BLACK, SIDE_WHITE, OthelloSettings

class OthelloSettingsOverlay(QWidget):
    back_requested = pyqtSignal()
    settings_applied = pyqtSignal(object)

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)

        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("othelloSettingsRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        panel.setMinimumWidth(640)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("OTHELLO SETTINGS", panel)
        title.setObjectName("title")
        title_row.addWidget(title)
        title_row.addStretch(1)

        btn_cancel = QPushButton("Cancel", panel)
        btn_cancel.setObjectName("menuBtn")
        btn_cancel.clicked.connect(self.back_requested.emit)
        title_row.addWidget(btn_cancel)
        layout.addLayout(title_row)

        subtitle = QLabel("These settings are stored immediately and take effect the next time Start is used.", panel)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        sep = QFrame(panel)
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._difficulty = self._add_combo(layout, panel, "AI difficulty",((OTHELLO_DIFFICULTY_WEAK, "Weak"),(OTHELLO_DIFFICULTY_MEDIUM, "Medium"),(OTHELLO_DIFFICULTY_STRONG, "Strong"),(OTHELLO_DIFFICULTY_INSANE, "Insane")))
        self._time_control = self._add_combo(layout, panel, "Time control",((OTHELLO_TIME_CONTROL_PER_SIDE_20M, "20 minutes per side"),(OTHELLO_TIME_CONTROL_NONE, "No limit")))
        self._player_side = self._add_combo(layout, panel, "Player order",((SIDE_BLACK, "Player moves first"),(SIDE_WHITE, "Player moves second")))

        btn_save = QPushButton("Save", panel)
        btn_save.setObjectName("menuBtn")
        btn_save.clicked.connect(self._save_and_close)
        layout.addWidget(btn_save)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

        self.sync_values(OthelloSettings())

    @staticmethod
    def _add_combo(layout: QVBoxLayout, parent: QWidget, label_text: str, entries: tuple[tuple[object, str], ...]) -> QComboBox:
        label = QLabel(str(label_text), parent)
        label.setObjectName("valueLabel")
        layout.addWidget(label)

        combo = QComboBox(parent)
        for value, text in entries:
            combo.addItem(str(text), userData=value)
        layout.addWidget(combo)
        return combo

    def sync_values(self, settings: OthelloSettings) -> None:
        normalized = settings.normalized()
        self._set_combo_data(self._difficulty, normalized.difficulty)
        self._set_combo_data(self._time_control, normalized.time_control)
        self._set_combo_data(self._player_side, normalized.player_side)

    @staticmethod
    def _set_combo_data(combo: QComboBox, target_value: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == target_value:
                combo.blockSignals(True)
                combo.setCurrentIndex(index)
                combo.blockSignals(False)
                return

    def _save_and_close(self) -> None:
        settings = OthelloSettings(difficulty=str(self._difficulty.currentData()), time_control=str(self._time_control.currentData()), player_side=int(self._player_side.currentData())).normalized()
        self.settings_applied.emit(settings)
        self.back_requested.emit()

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.back_requested.emit()
            return
        super().keyPressEvent(e)