# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..hud.crosshair_art import CROSSHAIR_GRID_SIZE, CROSSHAIR_MODE_CUSTOM, CROSSHAIR_MODE_DEFAULT, EMPTY_CROSSHAIR_PIXELS, normalize_crosshair_pixels, render_crosshair_image

class CrosshairPreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode: str = CROSSHAIR_MODE_DEFAULT
        self._custom_pixels: tuple[str, ...] = EMPTY_CROSSHAIR_PIXELS
        self.setObjectName("crosshairPreview")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(96, 96)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def set_pattern(self, *, mode: object, custom_pixels: object) -> None:
        next_mode = CROSSHAIR_MODE_CUSTOM if str(mode or "").strip().lower() == CROSSHAIR_MODE_CUSTOM else CROSSHAIR_MODE_DEFAULT
        next_pixels = normalize_crosshair_pixels(custom_pixels)
        if next_mode == self._mode and next_pixels == self._custom_pixels:
            return
        self._mode = next_mode
        self._custom_pixels = next_pixels
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#151515"))
        painter.setPen(QPen(QColor("#353535"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        image = render_crosshair_image(self._mode, self._custom_pixels, scale=4)
        left = (int(self.width()) - int(image.width())) // 2
        top = (int(self.height()) - int(image.height())) // 2
        painter.drawImage(int(left), int(top), image)

class CrosshairPixelEditor(QWidget):
    pixels_changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixels: tuple[str, ...] = EMPTY_CROSSHAIR_PIXELS
        self._drag_value: str | None = None
        self.setObjectName("crosshairEditor")
        self.setMouseTracking(True)
        self.setMinimumSize(256, 256)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def pixels(self) -> tuple[str, ...]:
        return self._pixels

    def clear_pixels(self) -> None:
        self.set_pixels(EMPTY_CROSSHAIR_PIXELS)

    def set_pixels(self, pixels: object) -> None:
        normalized = normalize_crosshair_pixels(pixels)
        if normalized == self._pixels:
            return
        self._pixels = normalized
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(288, 288)

    def minimumSizeHint(self) -> QSize:
        return QSize(224, 224)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#111111"))

        cell = float(min(self.width(), self.height())) / float(CROSSHAIR_GRID_SIZE)
        size = cell * float(CROSSHAIR_GRID_SIZE)
        left = (float(self.width()) - size) * 0.5
        top = (float(self.height()) - size) * 0.5

        for y in range(CROSSHAIR_GRID_SIZE):
            for x in range(CROSSHAIR_GRID_SIZE):
                x0 = int(round(left + float(x) * cell))
                y0 = int(round(top + float(y) * cell))
                x1 = int(round(left + float(x + 1) * cell))
                y1 = int(round(top + float(y + 1) * cell))
                rect = (x0, y0, max(1, x1 - x0), max(1, y1 - y0))
                filled = self._pixels[y][x] == "1"
                painter.fillRect(*rect, QColor("#f4f4f4") if filled else QColor("#242424"))
                painter.setPen(QPen(QColor("#3d3d3d"), 1))
                painter.drawRect(x0, y0, max(0, x1 - x0 - 1), max(0, y1 - y0 - 1))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_value = "1"
            self._apply_event_point(event.position().x(), event.position().y())
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._drag_value = "0"
            self._apply_event_point(event.position().x(), event.position().y())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_value is not None:
            self._apply_event_point(event.position().x(), event.position().y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._drag_value = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_event_point(self, px: float, py: float) -> None:
        cell = float(min(self.width(), self.height())) / float(CROSSHAIR_GRID_SIZE)
        if cell <= 0.0:
            return
        size = cell * float(CROSSHAIR_GRID_SIZE)
        left = (float(self.width()) - size) * 0.5
        top = (float(self.height()) - size) * 0.5

        gx = int((float(px) - left) // cell)
        gy = int((float(py) - top) // cell)
        if gx < 0 or gy < 0 or gx >= int(CROSSHAIR_GRID_SIZE) or gy >= int(CROSSHAIR_GRID_SIZE):
            return
        if self._drag_value is None:
            return

        rows = [list(row) for row in self._pixels]
        if rows[gy][gx] == self._drag_value:
            return
        rows[gy][gx] = self._drag_value
        self._pixels = tuple("".join(row) for row in rows)
        self.update()
        self.pixels_changed.emit(self._pixels)