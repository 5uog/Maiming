# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from .viewport.gl_viewport_widget import GLViewportWidget
from .hud.hud_widget import HUDWidget

class _LoadingOverlay(QFrame):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setStyleSheet("QFrame#loadingOverlay { background: #121212; }" "QLabel#loadingTitle { color: #f4f4f4; font-size: 28px; font-weight: 700; }" "QLabel#loadingStatus { color: #c8c8c8; font-size: 14px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch(1)

        self._title = QLabel("Ludoxel", self)
        self._title.setObjectName("loadingTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._title)

        self._status = QLabel("Preparing viewport...", self)
        self._status.setObjectName("loadingStatus")
        self._status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._status)

        layout.addStretch(1)

    def set_status_text(self, text: str) -> None:
        self._status.setText(str(text).strip() or "Loading...")

class GameScreen(QWidget):
    def __init__(self, project_root: Path, parent=None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.setObjectName("gameScreen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#gameScreen { background: #121212; }")
        self.viewport = GLViewportWidget(project_root=self.project_root)
        self.hud = HUDWidget()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.viewport)

        self.viewport.set_hud(self.hud)
        self.viewport.hud_updated.connect(self.hud.set_payload)

        self._loading_overlay = _LoadingOverlay(self)
        self._loading_overlay.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        self._loading_overlay.set_status_text(self.viewport.loading_status_text())
        self._loading_overlay.setVisible(bool(self.viewport.loading_active()))
        self.viewport.loading_state_changed.connect(self._handle_loading_state_changed)
        self.viewport.loading_status_changed.connect(self._loading_overlay.set_status_text)
        self.viewport.loading_finished.connect(self._handle_loading_finished)
        self._loading_overlay.raise_()

        if not self.viewport.loading_active():
            self._handle_loading_finished()

    def _handle_loading_finished(self) -> None:
        self._loading_overlay.hide()
        self.viewport.setFocus(Qt.FocusReason.OtherFocusReason)

    def _handle_loading_state_changed(self, active: bool) -> None:
        self._loading_overlay.setVisible(bool(active))
        if bool(active):
            self._loading_overlay.raise_()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._loading_overlay.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        if self._loading_overlay.isVisible():
            self._loading_overlay.raise_()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._loading_overlay.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        if self._loading_overlay.isVisible():
            self._loading_overlay.raise_()