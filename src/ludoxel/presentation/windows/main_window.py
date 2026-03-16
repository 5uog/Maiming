# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/windows/main_window.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow

from ..config.gl_surface_format import install_default_gl_surface_format
from ..screens.game_screen import GameScreen
from ..theme.fonts import install_minecraft_fonts, apply_application_font


class MainWindow(QMainWindow):

    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self._project_root = Path(project_root)
        self._screen = GameScreen(project_root=self._project_root)
        self.setCentralWidget(self._screen)
        self._screen.viewport.fullscreen_changed.connect(self._apply_fullscreen)

    def wants_fullscreen(self) -> bool:
        return bool(self._screen.viewport.fullscreen_enabled())

    def _apply_fullscreen(self, on: bool) -> None:
        if bool(on):
            if not self.isFullScreen():
                self.showFullScreen()
            return

        if self.isFullScreen():
            self.showNormal()

    def closeEvent(self, e) -> None:
        try:
            self._screen.viewport.shutdown()
        except Exception:
            pass
        super().closeEvent(e)


def run_app(*, project_root: Path) -> None:
    install_default_gl_surface_format()

    root = Path(project_root)

    app = QApplication([])
    app.setApplicationName("Ludoxel v3")

    fonts = install_minecraft_fonts(font_dir=(root / "assets" / "fonts"))
    if bool(fonts.ok):
        apply_application_font(app=app, family=str(fonts.family), point_size=12)

    qss = Path(__file__).resolve().parents[1] / "theme" / "main.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    w = MainWindow(project_root=root)
    w.setWindowTitle("Ludoxel")
    w.resize(1280, 720)
    w.setMinimumSize(1280, 720)
    if bool(w.wants_fullscreen()):
        w.showFullScreen()
    else:
        w.show()

    app.exec()
