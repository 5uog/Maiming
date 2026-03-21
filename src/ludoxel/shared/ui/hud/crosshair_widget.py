# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget

from .crosshair_art import CROSSHAIR_MODE_DEFAULT, EMPTY_CROSSHAIR_PIXELS, render_crosshair_image

_GAME_CROSSHAIR_SCALE = 2

class CrosshairWidget(QWidget):
    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._mode = CROSSHAIR_MODE_DEFAULT
        self._custom_pixels: tuple[str, ...] = EMPTY_CROSSHAIR_PIXELS
        self._image = render_crosshair_image(self._mode, self._custom_pixels, scale=int(_GAME_CROSSHAIR_SCALE))

    def set_pattern(self, *, mode: object, custom_pixels: object) -> None:
        self._mode = str(mode or "")
        self._custom_pixels = tuple(str(row) for row in custom_pixels) if isinstance(custom_pixels, (list, tuple)) else EMPTY_CROSSHAIR_PIXELS
        self._image = render_crosshair_image(self._mode, self._custom_pixels, scale=int(_GAME_CROSSHAIR_SCALE))
        self.update()

    def paintEvent(self, _e) -> None:
        w = self.width()
        h = self.height()
        if w <= 1 or h <= 1 or self._image.isNull():
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        left = (int(w) - int(self._image.width())) // 2
        top = (int(h) - int(self._image.height())) // 2
        p.drawImage(int(left), int(top), self._image)
        p.end()