# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QSizePolicy, QWidget

from ...math.scalars import clampf

_HEAD_YAW_LIMIT_DEG = 55.0
_HEAD_PITCH_LIMIT_DEG = 35.0
_DRAG_YAW_SCALE_DEG_PER_PX = 0.9


class PlayerSkinPreviewWidget(QWidget):
    view_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._frame_image = QImage()
        self._body_yaw_deg = 0.0
        self._head_yaw_deg = 0.0
        self._head_pitch_deg = 0.0
        self._dragging = False
        self._drag_last_x = 0.0
        self._name_tag_text = ""
        self._name_tag_visible = False
        self._name_tag_center_x: float | None = None
        self._name_tag_bottom_y: float | None = None
        self.setObjectName("playerSkinPreview")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(280, 372)
        self.setMaximumSize(320, 432)

        self._name_tag = QLabel(self)
        self._name_tag.setObjectName("playerNameTag")
        self._name_tag.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._name_tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._name_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_tag.setVisible(False)
        self._name_tag_effect = QGraphicsOpacityEffect(self._name_tag)
        self._name_tag_effect.setOpacity(1.0)
        self._name_tag.setGraphicsEffect(self._name_tag_effect)

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
        if (not next_image.isNull() and not self._frame_image.isNull() and int(next_image.cacheKey()) == int(self._frame_image.cacheKey()) and abs(float(next_image.devicePixelRatio()) - float(self._frame_image.devicePixelRatio())) <= 1e-9):
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

    def note_pointer_left(self) -> None:
        return

    def note_pointer_entered(self, *, x: float, y: float, area_width: int, area_height: int) -> None:
        self._update_head_tracking(x=float(x), y=float(y), area_width=int(area_width), area_height=int(area_height))

    def reset_head_tracking(self) -> None:
        if self._dragging:
            return
        self._head_yaw_deg = 0.0
        self._head_pitch_deg = 0.0
        self._emit_view_changed()

    def resizeEvent(self, event) -> None:
        self._layout_name_tag()
        self.view_changed.emit()
        super().resizeEvent(event)

    def paintEvent(self, _event) -> None:
        if self._frame_image.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.drawImage(self.rect(), self._frame_image)

    def _head_target_from_pointer(self, *, x: float, y: float, area_width: int, area_height: int) -> tuple[float, float]:
        if int(area_width) <= 1 or int(area_height) <= 1:
            return (float(self._head_yaw_deg), float(self._head_pitch_deg))
        nx = ((float(x) / max(1.0, float(area_width))) - 0.5) * 2.0
        ny = ((float(y) / max(1.0, float(area_height))) - 0.5) * 2.0
        return (float(clampf(nx * float(_HEAD_YAW_LIMIT_DEG), -float(_HEAD_YAW_LIMIT_DEG), float(_HEAD_YAW_LIMIT_DEG))), float(clampf(ny * float(_HEAD_PITCH_LIMIT_DEG), -float(_HEAD_PITCH_LIMIT_DEG), float(_HEAD_PITCH_LIMIT_DEG))))

    def _update_head_tracking(self, *, x: float, y: float, area_width: int, area_height: int) -> None:
        target_head_yaw_deg, target_head_pitch_deg = self._head_target_from_pointer(x=float(x), y=float(y), area_width=int(area_width), area_height=int(area_height))
        if abs(float(target_head_yaw_deg) - float(self._head_yaw_deg)) <= 1e-6 and abs(float(target_head_pitch_deg) - float(self._head_pitch_deg)) <= 1e-6:
            return
        self._head_yaw_deg = float(target_head_yaw_deg)
        self._head_pitch_deg = float(target_head_pitch_deg)
        self._emit_view_changed()

    def _emit_view_changed(self) -> None:
        self.view_changed.emit()
        self.update()

    def set_name_tag(self, text: str, *, visible: bool, opacity: float = 1.0, center_x: float | None = None, bottom_y: float | None = None) -> None:
        self._name_tag_text = str(text).strip()
        self._name_tag_visible = bool(visible) and bool(self._name_tag_text)
        self._name_tag_center_x = None if center_x is None else float(center_x)
        self._name_tag_bottom_y = None if bottom_y is None else float(bottom_y)
        self._name_tag_effect.setOpacity(float(clampf(float(opacity), 0.0, 1.0)))
        self._layout_name_tag()

    def _layout_name_tag(self) -> None:
        if not bool(self._name_tag_visible):
            self._name_tag.setVisible(False)
            return
        self._name_tag.setText(str(self._name_tag_text))
        self._name_tag.adjustSize()
        label_w = int(max(1, self._name_tag.width()))
        label_h = int(max(1, self._name_tag.height()))
        center_x = float(self.width()) * 0.5 if self._name_tag_center_x is None else float(self._name_tag_center_x)
        bottom_y = float(self.height()) * 0.12 if self._name_tag_bottom_y is None else float(self._name_tag_bottom_y)
        x = int(round(float(center_x) - float(label_w) * 0.5))
        y = int(round(float(bottom_y) - float(label_h)))
        x = max(0, min(max(0, int(self.width()) - label_w), int(x)))
        y = max(0, min(max(0, int(self.height()) - label_h), int(y)))
        self._name_tag.setGeometry(int(x), int(y), int(label_w), int(label_h))
        self._name_tag.setVisible(True)
        self._name_tag.raise_()
