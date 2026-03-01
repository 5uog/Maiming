# FILE: src/maiming/presentation/widgets/hud/hud_widget.py
from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt

class HUDWidget(QLabel):
    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("hud")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setText("")

    def set_text(self, s: str) -> None:
        parent = self.parentWidget()
        pw = int(parent.width()) if parent is not None else 1280
        ph = int(parent.height()) if parent is not None else 720

        w = max(720, min(pw - 20, 1200))
        self.setFixedWidth(int(w))

        self.setText(str(s))
        self.adjustSize()

        h = int(self.sizeHint().height())
        h = max(90, min(h, ph - 20))
        self.setFixedHeight(int(h))