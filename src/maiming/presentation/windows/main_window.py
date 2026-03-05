# FILE: src/maiming/presentation/windows/main_window.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QSurfaceFormat
from PyQt6.QtWidgets import QApplication, QMainWindow

from maiming.presentation.screens.game_screen import GameScreen
from maiming.presentation.theme.fonts import install_minecraft_fonts, apply_application_font

def _set_default_gl_format() -> None:
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(4)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    QSurfaceFormat.setDefaultFormat(fmt)

class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self._project_root = Path(project_root)
        self._screen = GameScreen(project_root=self._project_root)
        self.setCentralWidget(self._screen)

    def closeEvent(self, e) -> None:
        try:
            self._screen.viewport.shutdown()
        except Exception:
            pass
        super().closeEvent(e)

def run_app(*, project_root: Path) -> None:
    _set_default_gl_format()

    root = Path(project_root)

    app = QApplication([])
    app.setApplicationName("Maiming v2.5")

    fonts = install_minecraft_fonts(font_dir=(root / "assets" / "fonts"))
    if bool(fonts.ok):
        apply_application_font(app=app, family=str(fonts.family), point_size=12)

    qss = Path(__file__).resolve().parents[1] / "theme" / "main.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    w = MainWindow(project_root=root)
    w.setWindowTitle("Maiming v2.5")
    w.resize(1280, 720)
    w.show()

    app.exec()