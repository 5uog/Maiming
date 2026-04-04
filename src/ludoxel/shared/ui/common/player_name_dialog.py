# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QFrame, QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ....application.runtime.player_name import normalize_player_name


class PlayerNameDialog(QDialog):

    def __init__(self, *, title_image_path: Path | None = None, initial_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playerNameDialog")
        self.setWindowTitle("Player Name")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.Dialog, True)
        self.setWindowFlag(Qt.WindowType.CustomizeWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowTitleHint, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.resize(520, 360)
        self.setMinimumSize(460, 320)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        panel = QFrame(self)
        panel.setObjectName("playerNamePanel")
        root.addWidget(panel, stretch=1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)

        self._title_image = QLabel(panel)
        self._title_image.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._title_image.setVisible(False)
        layout.addWidget(self._title_image, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._title_label = QLabel("Set Player Name", panel)
        self._title_label.setObjectName("playerNameTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._title_label)

        self._subtitle = QLabel("Leave the field blank to continue with a new random session name each time the application starts.", panel)
        self._subtitle.setObjectName("playerNameSubtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._subtitle)

        self._name_edit = QLineEdit(panel)
        self._name_edit.setObjectName("playerNameEdit")
        self._name_edit.setPlaceholderText("Player name")
        self._name_edit.setClearButtonEnabled(True)
        self._name_edit.setText(normalize_player_name(initial_name))
        self._name_edit.returnPressed.connect(self.accept)
        layout.addWidget(self._name_edit)

        layout.addStretch(1)

        continue_button = QPushButton("Continue", panel)
        continue_button.setObjectName("playerNameContinue")
        continue_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        continue_button.clicked.connect(self.accept)
        layout.addWidget(continue_button)

        self.set_title_image_path(title_image_path)

    def selected_player_name(self) -> str:
        return normalize_player_name(self._name_edit.text())

    def set_title_image_path(self, path: Path | None) -> None:
        pixmap = QPixmap()
        if path is not None:
            pixmap = QPixmap(str(Path(path).resolve()))
        if pixmap.isNull():
            self._title_image.clear()
            self._title_image.setVisible(False)
            return
        scaled = pixmap.scaled(320, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._title_image.setPixmap(scaled)
        self._title_image.setVisible(True)
