# FILE: src/maiming/presentation/widgets/overlays/pause_overlay.py
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)

class PauseOverlay(QWidget):
    resume_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
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

        subtitle = QLabel("Resume the session or open Settings.", panel)
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

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.resume_requested.emit()
            return
        super().keyPressEvent(e)