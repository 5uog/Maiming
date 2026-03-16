# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/hud/crosshair_widget.py
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget


class CrosshairWidget(QWidget):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._gap = 6
        self._arm = 10
        self._thick = 2
        self._outline = 3

    def paintEvent(self, _e) -> None:
        w = self.width()
        h = self.height()
        if w <= 1 or h <= 1:
            return

        cx = w * 0.5
        cy = h * 0.5

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        def draw_with_pen(pen: QPen) -> None:
            p.setPen(pen)

            p.drawLine(int(cx - self._gap - self._arm), int(cy), int(cx - self._gap), int(cy))
            p.drawLine(int(cx + self._gap), int(cy), int(cx + self._gap + self._arm), int(cy))

            p.drawLine(int(cx), int(cy - self._gap - self._arm), int(cx), int(cy - self._gap))
            p.drawLine(int(cx), int(cy + self._gap), int(cx), int(cy + self._gap + self._arm))

        outline_pen = QPen(QColor(0, 0, 0, 200))
        outline_pen.setWidth(max(1, int(self._outline)))
        draw_with_pen(outline_pen)

        main_pen = QPen(QColor(255, 255, 255, 230))
        main_pen.setWidth(max(1, int(self._thick)))
        draw_with_pen(main_pen)

        p.end()
