# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen

def build_special_item_icon_image(icon_key: str, *, size: int) -> QImage:
    icon_size = int(max(16, int(size)))
    image = QImage(icon_size, icon_size, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    margin = max(2.0, float(icon_size) * 0.08)
    frame_rect = image.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))

    painter.setPen(QPen(QColor("#0f0f0f"), max(1, icon_size // 18)))
    painter.setBrush(QColor("#2a2a2a"))
    painter.drawRoundedRect(frame_rect, 4.0, 4.0)

    normalized = str(icon_key).strip().lower()
    if normalized == "start":
        _paint_start_icon(painter, frame_rect)
    else:
        _paint_settings_icon(painter, frame_rect)

    painter.end()
    return image

def _paint_start_icon(painter: QPainter, rect) -> None:
    painter.setPen(QPen(QColor("#14360b"), 1))
    painter.setBrush(QColor("#71b442"))

    width = float(rect.width())
    height = float(rect.height())
    left = float(rect.left())
    top = float(rect.top())

    path = QPainterPath()
    path.moveTo(left + width * 0.30, top + height * 0.22)
    path.lineTo(left + width * 0.30, top + height * 0.78)
    path.lineTo(left + width * 0.76, top + height * 0.50)
    path.closeSubpath()
    painter.drawPath(path)

def _paint_settings_icon(painter: QPainter, rect) -> None:
    width = float(rect.width())
    height = float(rect.height())
    left = float(rect.left())
    top = float(rect.top())

    painter.setPen(QPen(QColor("#f1f1f1"), max(2, rect.width() // 12)))
    for row_index, knob_offset in enumerate((0.30, 0.62, 0.44)):
        y = top + height * (0.28 + 0.22 * row_index)
        painter.drawLine(int(left + width * 0.20), int(y), int(left + width * 0.80), int(y))
        painter.setBrush(QColor("#d5d5d5"))
        x = left + width * float(knob_offset)
        radius = max(2.0, width * 0.08)
        painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2.0), int(radius * 2.0))