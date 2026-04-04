# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import sys

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QIcon, QScreen
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

from ...application.boot.meta import __version__
from ...application.runtime.persistence.app_state_store import AppStateStore
from ...application.runtime.player_name import normalize_player_name
from .common.status_overlay import StatusOverlayFrame, status_overlay_title_image_path
from .common.player_name_dialog import PlayerNameDialog
from .common.single_instance import SingleInstanceRelay
from .config.gl_surface_format import install_default_gl_surface_format
from .game_screen import GameScreen
from .theme.fonts import install_minecraft_fonts, apply_application_font

_MIN_WINDOW_WIDTH = 980
_MIN_WINDOW_HEIGHT = 620
_APP_ICON_CANDIDATE_NAMES = ("app_icon.ico", "app_icon.png", "app_icon.jpg", "app_icon.jpeg")


def _application_icon_candidate_paths(resource_root: Path) -> tuple[Path, ...]:
    base = Path(resource_root) / "assets" / "ui"
    return tuple(base / name for name in _APP_ICON_CANDIDATE_NAMES)


def _load_application_icon(resource_root: Path) -> QIcon | None:
    for path in _application_icon_candidate_paths(resource_root):
        if not path.is_file():
            continue
        icon = QIcon(str(path.resolve()))
        if not icon.isNull():
            return icon
    return None


def _set_windows_application_id() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KentoKonishi.Ludoxel")
    except Exception:
        pass


def _request_widget_activation(widget: QWidget | None) -> None:
    if widget is None:
        return
    if hasattr(widget, "request_activation"):
        widget.request_activation()
        return
    if widget.isMinimized():
        widget.showNormal()
    else:
        widget.show()
    widget.raise_()
    widget.activateWindow()
    handle = widget.windowHandle()
    if handle is not None:
        handle.requestActivate()


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
        clamped_left = int(available.x() + max(0,(int(available.width()) - clamped_width) // 2))
    else:
        clamped_left = int(max(int(available.left()), min(int(left), int(available.right()) - clamped_width + 1)))

    if top is None:
        clamped_top = int(available.y() + max(0,(int(available.height()) - clamped_height) // 2))
    else:
        clamped_top = int(max(int(available.top()), min(int(top), int(available.bottom()) - clamped_height + 1)))

    return QRect(int(clamped_left), int(clamped_top), int(clamped_width), int(clamped_height))


class MainWindow(QMainWindow):

    def __init__(self, project_root: Path, resource_root: Path, *, launch_player_name: str | None = None) -> None:
        super().__init__()
        self._project_root = Path(project_root)
        self._resource_root = Path(resource_root)
        self._screen = GameScreen(project_root=self._project_root, resource_root=self._resource_root, launch_player_name=launch_player_name)
        self.setCentralWidget(self._screen)
        self.setMinimumSize(_MIN_WINDOW_WIDTH, _MIN_WINDOW_HEIGHT)
        self._screen.viewport.fullscreen_changed.connect(self._apply_fullscreen)

    def wants_fullscreen(self) -> bool:
        return bool(self._screen.viewport.fullscreen_enabled())

    def runtime_preferences(self):
        return self._screen.viewport._state

    def request_activation(self) -> None:
        if self.isMinimized():
            self.showNormal()
        elif bool(self.wants_fullscreen()):
            self.showFullScreen()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        handle = self.windowHandle()
        if handle is not None:
            handle.requestActivate()
        for overlay in (self._screen.viewport._settings, self._screen.viewport._othello_settings):
            if overlay is not None and overlay.isVisible():
                _request_widget_activation(overlay)
        self._screen.viewport.arm_resume_refresh()

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


def run_app(*, project_root: Path, resource_root: Path) -> None:
    install_default_gl_surface_format()

    root = Path(project_root)
    bundled_root = Path(resource_root)

    _set_windows_application_id()
    app = QApplication([])
    app.setApplicationName(f"Ludoxel v{__version__}")
    app_icon = _load_application_icon(bundled_root)
    if app_icon is not None:
        app.setWindowIcon(app_icon)

    fonts = install_minecraft_fonts(font_dir=(bundled_root / "assets" / "fonts"))
    if bool(fonts.ok):
        apply_application_font(app=app, family=str(fonts.family), point_size=12, fallback_families=tuple(fonts.fallback_families))

    qss = Path(__file__).resolve().parent / "theme" / "main.qss"
    if qss.exists():
        qss_text = qss.read_text(encoding="utf-8")
        arrow_up = (bundled_root / "assets" / "ui" / "arrow_up.svg").resolve().as_posix()
        arrow_down = (bundled_root / "assets" / "ui" / "arrow_down.svg").resolve().as_posix()
        qss_text = qss_text.replace("__ARROW_UP__", str(arrow_up))
        qss_text = qss_text.replace("__ARROW_DOWN__", str(arrow_down))
        app.setStyleSheet(qss_text)

    relay = SingleInstanceRelay(root, app)
    if relay.activate_existing_instance():
        return
    relay.listen()
    app.aboutToQuit.connect(relay.close)
    activation_handler: dict[str, object] = {"callback": None}

    def _set_activation_callback(callback) -> None:
        activation_handler["callback"] = callback

    def _handle_activation_request() -> None:
        callback = activation_handler.get("callback")
        if callable(callback):
            callback()

    relay.activation_requested.connect(_handle_activation_request)

    persisted_state = AppStateStore(project_root=root).load()
    explicit_player_name = ""
    if persisted_state is not None:
        explicit_player_name = normalize_player_name(persisted_state.settings.player_name)

    splash_title_image_path = status_overlay_title_image_path(bundled_root)
    launch_player_name = explicit_player_name
    if not launch_player_name:
        dialog = PlayerNameDialog(title_image_path=splash_title_image_path, initial_name=explicit_player_name)
        if app_icon is not None:
            dialog.setWindowIcon(app_icon)
        _set_activation_callback(lambda current=dialog: _request_widget_activation(current))
        if not bool(dialog.exec()):
            return
        launch_player_name = dialog.selected_player_name()

    w = MainWindow(project_root=root, resource_root=bundled_root, launch_player_name=launch_player_name)
    _set_activation_callback(w.request_activation)
    if app_icon is not None:
        w.setWindowIcon(app_icon)
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

    splash = StatusOverlayFrame(title_text="Ludoxel", status_text="Preparing viewport...", object_name="startupSplash", title_object_name="startupTitle", status_object_name="startupStatus", title_image_path=splash_title_image_path, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
    if app_icon is not None:
        splash.setWindowIcon(app_icon)
    splash.setGeometry(splash_geometry)
    _set_activation_callback(lambda main_window=w, splash_widget=splash: (_request_widget_activation(main_window), _request_widget_activation(splash_widget)))
    splash.show()
    splash.raise_()
    app.processEvents()

    viewport = w._screen.viewport
    viewport.loading_status_changed.connect(splash.set_status_text)
    viewport.loading_finished.connect(splash.close)
    viewport.loading_finished.connect(lambda: _set_activation_callback(w.request_activation))
    splash.set_status_text(viewport.loading_status_text())
    if bool(w.wants_fullscreen()):
        w.showFullScreen()
    else:
        w.show()
    splash.raise_()

    app.exec()
