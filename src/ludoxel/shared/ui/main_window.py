# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QMainWindow, QVBoxLayout

from ...application.boot.meta import __version__
from .config.gl_surface_format import install_default_gl_surface_format
from .game_screen import GameScreen
from .theme.fonts import install_minecraft_fonts, apply_application_font

_MIN_WINDOW_WIDTH = 980
_MIN_WINDOW_HEIGHT = 620

class _StartupSplash(QFrame):
    def __init__(self, *, status_text: str) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        self.setObjectName("startupSplash")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QFrame#startupSplash { background: #121212; }" "QLabel#startupTitle { color: #f4f4f4; font-size: 28px; font-weight: 700; }" "QLabel#startupStatus { color: #c8c8c8; font-size: 14px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch(1)

        title = QLabel("Ludoxel", self)
        title.setObjectName("startupTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        self._status = QLabel("", self)
        self._status.setObjectName("startupStatus")
        self._status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._status)

        layout.addStretch(1)
        self.set_status_text(status_text)

    def set_status_text(self, text: str) -> None:
        self._status.setText(str(text).strip() or "Loading...")


def _screen_for_restore(app: QApplication, *, screen_name: str, left: int | None, top: int | None, width: int, height: int) -> QScreen | None:
    normalized_name = str(screen_name or "").strip()
    if normalized_name:
        for screen in app.screens():
            if str(screen.name()) == normalized_name:
                return screen

    if left is not None and top is not None:
        center = QPoint(int(left) + max(0, int(width) // 2), int(top) + max(0, int(height) // 2))
        screen = QApplication.screenAt(center)
        if screen is not None:
            return screen

    return app.primaryScreen()


def _restored_window_geometry(screen: QScreen | None, *, left: int | None, top: int | None, width: int, height: int) -> QRect:
    fallback = QRect(0, 0, max(_MIN_WINDOW_WIDTH, int(width)), max(_MIN_WINDOW_HEIGHT, int(height)))
    if screen is None:
        return fallback

    available = screen.availableGeometry()
    clamped_width = max(_MIN_WINDOW_WIDTH, min(int(width), int(available.width())))
    clamped_height = max(_MIN_WINDOW_HEIGHT, min(int(height), int(available.height())))

    if left is None:
        clamped_left = int(available.x() + max(0, (int(available.width()) - clamped_width) // 2))
    else:
        clamped_left = int(max(int(available.left()), min(int(left), int(available.right()) - clamped_width + 1)))

    if top is None:
        clamped_top = int(available.y() + max(0, (int(available.height()) - clamped_height) // 2))
    else:
        clamped_top = int(max(int(available.top()), min(int(top), int(available.bottom()) - clamped_height + 1)))

    return QRect(int(clamped_left), int(clamped_top), int(clamped_width), int(clamped_height))

class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self._project_root = Path(project_root)
        self._screen = GameScreen(project_root=self._project_root)
        self.setCentralWidget(self._screen)
        self.setMinimumSize(_MIN_WINDOW_WIDTH, _MIN_WINDOW_HEIGHT)
        self._screen.viewport.fullscreen_changed.connect(self._apply_fullscreen)

    def wants_fullscreen(self) -> bool:
        return bool(self._screen.viewport.fullscreen_enabled())

    def runtime_preferences(self):
        return self._screen.viewport._state

    def _persist_window_geometry(self) -> None:
        geometry = self.normalGeometry() if self.isFullScreen() and self.normalGeometry().isValid() else self.geometry()
        screen = None
        handle = self.windowHandle()
        if handle is not None:
            screen = handle.screen()
        if screen is None:
            center = self.mapToGlobal(self.rect().center())
            screen = QApplication.screenAt(center)
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_name = "" if screen is None else str(screen.name())
        self._screen.viewport.record_host_window_geometry(left=int(geometry.x()), top=int(geometry.y()), width=int(geometry.width()), height=int(geometry.height()), screen_name=screen_name)

    def _apply_fullscreen(self, on: bool) -> None:
        if bool(on):
            if not self.isFullScreen():
                self.showFullScreen()
            return

        if self.isFullScreen():
            self.showNormal()

    def closeEvent(self, e) -> None:
        try:
            self._persist_window_geometry()
            self._screen.viewport.shutdown()
        except Exception:
            pass
        super().closeEvent(e)

    def moveEvent(self, e) -> None:
        super().moveEvent(e)
        if self.isVisible() and not self.isFullScreen():
            self._persist_window_geometry()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if self.isVisible() and not self.isFullScreen():
            self._persist_window_geometry()

def run_app(*, project_root: Path) -> None:
    install_default_gl_surface_format()

    root = Path(project_root)

    app = QApplication([])
    app.setApplicationName(f"Ludoxel v{__version__}")

    fonts = install_minecraft_fonts(font_dir=(root / "assets" / "fonts"))
    if bool(fonts.ok):
        apply_application_font(app=app, family=str(fonts.family), point_size=12)

    qss = Path(__file__).resolve().parent / "theme" / "main.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    w = MainWindow(project_root=root)
    w.setWindowTitle(f"Ludoxel v{__version__}")
    prefs = w.runtime_preferences()
    restore_screen = _screen_for_restore(app, screen_name=str(prefs.window_screen_name), left=prefs.window_left, top=prefs.window_top, width=int(prefs.window_width), height=int(prefs.window_height))
    restore_geometry = _restored_window_geometry(restore_screen, left=prefs.window_left, top=prefs.window_top, width=int(prefs.window_width), height=int(prefs.window_height))
    if bool(w.wants_fullscreen()) and restore_screen is not None:
        splash_geometry = restore_screen.availableGeometry()
        w.setGeometry(splash_geometry)
    else:
        splash_geometry = restore_geometry
        w.setGeometry(restore_geometry)

    splash = _StartupSplash(status_text="Preparing viewport...")
    splash.setGeometry(splash_geometry)
    splash.show()
    splash.raise_()
    app.processEvents()

    viewport = w._screen.viewport
    viewport.loading_status_changed.connect(splash.set_status_text)
    viewport.loading_finished.connect(splash.close)
    splash.set_status_text(viewport.loading_status_text())
    if bool(w.wants_fullscreen()):
        w.showFullScreen()
    else:
        w.show()
    splash.raise_()

    app.exec()