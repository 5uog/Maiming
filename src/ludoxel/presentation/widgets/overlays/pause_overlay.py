# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/overlays/pause_overlay.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy

from ....domain.play_space import PLAY_SPACE_MY_WORLD, is_othello_space, is_my_world_space, normalize_play_space_id


class PauseOverlay(QWidget):
    resume_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    play_my_world_requested = pyqtSignal()
    play_othello_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)

        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("pauseRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        panel.setMinimumWidth(520)

        pv = QVBoxLayout(panel)
        pv.setContentsMargins(20, 18, 20, 20)
        pv.setSpacing(12)

        title = QLabel("PAUSED", panel)
        title.setObjectName("title")
        pv.addWidget(title)

        subtitle = QLabel("Resume the session, switch play spaces, or open Settings.", panel)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        pv.addWidget(subtitle)

        sep = QFrame(panel)
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        pv.addWidget(sep)

        btn_resume = QPushButton("Resume", panel)
        btn_resume.setObjectName("menuBtn")
        btn_resume.clicked.connect(self.resume_requested.emit)
        pv.addWidget(btn_resume)

        btn_settings = QPushButton("Settings", panel)
        btn_settings.setObjectName("menuBtn")
        btn_settings.clicked.connect(self.settings_requested.emit)
        pv.addWidget(btn_settings)

        self._btn_my_world = QPushButton("Play My World", panel)
        self._btn_my_world.setObjectName("menuBtn")
        self._btn_my_world.clicked.connect(self.play_my_world_requested.emit)
        pv.addWidget(self._btn_my_world)

        self._btn_othello = QPushButton("Play Othello (Reversi)", panel)
        self._btn_othello.setObjectName("menuBtn")
        self._btn_othello.clicked.connect(self.play_othello_requested.emit)
        pv.addWidget(self._btn_othello)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

        self.set_current_space(PLAY_SPACE_MY_WORLD)

    def set_current_space(self, space_id: str) -> None:
        normalized = normalize_play_space_id(space_id)
        self._btn_my_world.setEnabled(not is_my_world_space(normalized))
        self._btn_othello.setEnabled(not is_othello_space(normalized))

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.resume_requested.emit()
            return
        super().keyPressEvent(e)
