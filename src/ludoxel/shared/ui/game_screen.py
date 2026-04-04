# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .common.status_overlay import StatusOverlayFrame, status_overlay_title_image_path
from .viewport.gl_viewport_widget import GLViewportWidget
from .hud.hud_widget import HUDWidget


class GameScreen(QWidget):

    def __init__(self, project_root: Path, resource_root: Path, parent=None, launch_player_name: str | None = None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.resource_root = resource_root
        self.setObjectName("gameScreen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#gameScreen { background: #121212; }")
        self.viewport = GLViewportWidget(project_root=self.project_root, resource_root=self.resource_root, launch_player_name=launch_player_name)
        self.hud = HUDWidget()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.viewport)

        self.viewport.set_hud(self.hud)
        self.viewport.hud_updated.connect(self.hud.set_payload)

        title_image_path = status_overlay_title_image_path(self.resource_root)
        self._loading_overlay = StatusOverlayFrame(title_text="Ludoxel", status_text="Preparing viewport...", object_name="loadingOverlay", title_object_name="loadingTitle", status_object_name="loadingStatus", title_image_path=title_image_path, parent=self)
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
