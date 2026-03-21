# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy

class DeathOverlay(QWidget):
    respawn_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)

        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("deathRoot")

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

        title = QLabel("YOU DIED", panel)
        title.setObjectName("title")
        pv.addWidget(title)

        msg = QLabel("You fell below the world. Respawn returns you to the session spawn position.", panel)
        msg.setWordWrap(True)
        pv.addWidget(msg)

        btn_row = QHBoxLayout()
        btn = QPushButton("Respawn", panel)
        btn.clicked.connect(self.respawn_requested.emit)
        btn_row.addWidget(btn)
        btn_row.addStretch(1)
        pv.addLayout(btn_row)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)