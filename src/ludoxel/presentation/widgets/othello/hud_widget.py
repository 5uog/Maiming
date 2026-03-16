# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/othello/hud_widget.py
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidget


class OthelloHudWidget(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._label = QLabel(self)
        self._label.setObjectName("othelloHud")
        self._label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._label.setWordWrap(True)
        self._label.setText("")

        self._title_label = QLabel(self)
        self._title_label.setObjectName("othelloTitle")
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setText("")

    def set_text(self, text: str) -> None:
        self._label.setText(str(text))
        self._relayout()

    def set_title_text(self, text: str) -> None:
        self._title_label.setText(str(text))
        self._relayout()

    def resizeEvent(self, _event) -> None:
        self._relayout()

    def _relayout(self) -> None:
        hud_text = str(self._label.text()).strip()
        title_text = str(self._title_label.text()).strip()

        if hud_text:
            width = min(420, max(220, self.width() // 3))
            self._label.setGeometry(14, 14, int(width), max(90, self._label.sizeHint().height() + 12))
            self._label.setVisible(True)
            self._label.raise_()
        else:
            self._label.setVisible(False)

        if title_text:
            width = min(680, max(320, self.width() // 2))
            height = max(64, self._title_label.sizeHint().height() + 18)
            x = max(0, (self.width() - int(width)) // 2)
            y = max(0, (self.height() - int(height)) // 2)
            self._title_label.setGeometry(int(x), int(y), int(width), int(height))
            self._title_label.setVisible(True)
            self._title_label.raise_()
        else:
            self._title_label.setVisible(False)
