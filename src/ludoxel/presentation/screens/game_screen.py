# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/screens/game_screen.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout

from ..widgets.viewport.gl_viewport_widget import GLViewportWidget
from ..widgets.hud.hud_widget import HUDWidget


class GameScreen(QWidget):

    def __init__(self, project_root: Path, parent=None) -> None:
        super().__init__(parent)
        self.project_root = project_root

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.viewport = GLViewportWidget(project_root=self.project_root)
        self.hud = HUDWidget()

        layout.addWidget(self.viewport)
        self.viewport.set_hud(self.hud)
        self.viewport.hud_updated.connect(self.hud.set_payload)
