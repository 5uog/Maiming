# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

_HEAD_YAW_LIMIT_DEG = 55.0
_HEAD_PITCH_LIMIT_DEG = 35.0
_DRAG_YAW_SCALE_DEG_PER_PX = 0.9

class PlayerSkinPreviewWidget(QWidget):
    view_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame_image = QImage()
        self._body_yaw_deg = 0.0
        self._head_yaw_deg = 0.0
        self._head_pitch_deg = 0.0
        self._dragging = False
        self._drag_last_x = 0.0
        self.setObjectName("playerSkinPreview")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(280, 372)
        self.setMaximumSize(320, 432)

    def sizeHint(self) -> QSize:
        return QSize(300, 412)

    def minimumSizeHint(self) -> QSize:
        return QSize(280, 372)

    def set_skin(self, image: QImage, *, slim_arm: bool) -> None:
        del image, slim_arm

    def set_frame_image(self, image: QImage) -> None:
        next_image = QImage(image)
        if next_image.isNull() and self._frame_image.isNull():
            return
        self._frame_image = next_image
        self.update()

    def preview_angles(self) -> tuple[float, float, float]:
        return (float(self._body_yaw_deg), float(self._head_yaw_deg), float(self._head_pitch_deg))

    def begin_drag(self, *, x: float) -> None:
        self._dragging = True
        self._drag_last_x = float(x)

    def move_pointer(self, *, x: float, y: float, area_width: int, area_height: int) -> None:
        if self._dragging:
            dx = float(x) - float(self._drag_last_x)
            self._drag_last_x = x
            self._body_yaw_deg = float(self._body_yaw_deg + dx * float(_DRAG_YAW_SCALE_DEG_PER_PX)) % 360.0
            self._head_yaw_deg = 0.0
            self._head_pitch_deg = 0.0
            self._emit_view_changed()
            return

        self._update_head_tracking(x=float(x), y=float(y), area_width=int(area_width), area_height=int(area_height))

    def end_drag(self, *, x: float, y: float, area_width: int, area_height: int) -> None:
        self._dragging = False
        self._update_head_tracking(x=float(x), y=float(y), area_width=int(area_width), area_height=int(area_height))

    def reset_head_tracking(self) -> None:
        if self._dragging:
            return
        self._head_yaw_deg = 0.0
        self._head_pitch_deg = 0.0
        self._emit_view_changed()

    def resizeEvent(self, event) -> None:
        self.view_changed.emit()
        super().resizeEvent(event)

    def paintEvent(self, _event) -> None:
        if self._frame_image.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.drawImage(self.rect(), self._frame_image)

    def _update_head_tracking(self, *, x: float, y: float, area_width: int, area_height: int) -> None:
        if int(area_width) <= 1 or int(area_height) <= 1:
            return
        nx = ((float(x) / max(1.0, float(area_width))) - 0.5) * 2.0
        ny = ((float(y) / max(1.0, float(area_height))) - 0.5) * 2.0
        yaw_offset = max(-float(_HEAD_YAW_LIMIT_DEG), min(float(_HEAD_YAW_LIMIT_DEG), nx * float(_HEAD_YAW_LIMIT_DEG)))
        pitch = max(-float(_HEAD_PITCH_LIMIT_DEG), min(float(_HEAD_PITCH_LIMIT_DEG), ny * float(_HEAD_PITCH_LIMIT_DEG)))
        next_head_yaw = float(yaw_offset)
        next_head_pitch = float(pitch)
        if float(next_head_yaw) == float(self._head_yaw_deg) and float(next_head_pitch) == float(self._head_pitch_deg):
            return
        self._head_yaw_deg = float(next_head_yaw)
        self._head_pitch_deg = float(next_head_pitch)
        self._emit_view_changed()

    def _emit_view_changed(self) -> None:
        self.view_changed.emit()
        self.update()