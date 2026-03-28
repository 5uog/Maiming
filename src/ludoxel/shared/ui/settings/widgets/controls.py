# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFocusEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PyQt6.QtWidgets import QAbstractButton, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider, QWidget

from .....application.runtime.keybinds import display_text_for_binding, normalize_binding_text, normalize_key_code


def _draw_bedrock_frame(painter: QPainter, rect: QRect, *, fill: QColor, top_left: QColor, bottom_right: QColor, outline: QColor) -> None:
    if rect.width() <= 0 or rect.height() <= 0:
        return

    painter.fillRect(rect, fill)
    painter.setPen(QPen(outline, 1))
    painter.drawRect(rect)

    if rect.width() >= 2 and rect.height() >= 2:
        inner = rect.adjusted(1, 1, -1, -1)
        painter.setPen(QPen(top_left, 1))
        painter.drawLine(inner.topLeft(), inner.topRight())
        painter.drawLine(inner.topLeft(), inner.bottomLeft())
        painter.setPen(QPen(bottom_right, 1))
        painter.drawLine(inner.bottomLeft(), inner.bottomRight())
        painter.drawLine(inner.topRight(), inner.bottomRight())


class WheelPassthroughSlider(QSlider):

    _TRACK_HEIGHT = 16
    _HANDLE_SIZE = 24
    _PREFERRED_HEIGHT = 34

    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None=None) -> None:
        super().__init__(orientation, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(int(self._PREFERRED_HEIGHT))

    def sizeHint(self) -> QSize:
        return QSize(max(160, int(super().sizeHint().width())), int(self._PREFERRED_HEIGHT))

    def minimumSizeHint(self) -> QSize:
        return QSize(96, int(self._PREFERRED_HEIGHT))

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), self.palette().window())

        if self.orientation() != Qt.Orientation.Horizontal:
            super().paintEvent(_event)
            return

        handle_side = int(self._HANDLE_SIZE)
        track_height = int(self._TRACK_HEIGHT)
        half_handle = int(handle_side // 2)
        track_left = int(half_handle)
        track_right = int(max(track_left + 1, self.width() - half_handle))
        track = QRect(int(track_left), int((self.height() - track_height) // 2), int(max(1, track_right - track_left)), int(track_height))

        hovered = bool(self.underMouse())
        enabled = bool(self.isEnabled())

        off_fill = QColor("#505050")
        off_light = QColor("#8C8C8C")
        off_dark = QColor("#1A1A1A")
        on_fill = QColor("#6FB03A")
        on_light = QColor("#A9D46A")
        on_dark = QColor("#254114")
        thumb_fill = QColor("#E0E0E0")
        thumb_light = QColor("#FFFFFF")
        thumb_dark = QColor("#5C5C5C")

        if hovered and enabled:
            off_fill = off_fill.lighter(106)
            on_fill = on_fill.lighter(106)
            thumb_fill = thumb_fill.lighter(105)

        if not enabled:
            off_fill = QColor("#636363")
            off_light = QColor("#8E8E8E")
            off_dark = QColor("#303030")
            on_fill = QColor("#7A8F65")
            on_light = QColor("#A2B58F")
            on_dark = QColor("#38442F")

        _draw_bedrock_frame(painter, track, fill=off_fill, top_left=off_light, bottom_right=off_dark, outline=QColor("#0b0b0b"))

        value_span = int(self.maximum() - self.minimum())
        ratio = 0.0 if value_span <= 0 else float(self.value() - self.minimum()) / float(value_span)
        ratio = max(0.0, min(1.0, float(ratio)))

        inner = track.adjusted(1, 1, -1, -1)
        if inner.width() > 0 and inner.height() > 0:
            active_width = int(round(float(inner.width()) * float(ratio)))
            if active_width > 0:
                active = QRect(int(inner.x()), int(inner.y()), int(active_width), int(inner.height()))
                painter.fillRect(active, on_fill)
                if active.height() >= 2:
                    painter.setPen(QPen(on_light, 1))
                    painter.drawLine(active.topLeft(), active.topRight())
                    painter.setPen(QPen(on_dark, 1))
                    painter.drawLine(active.bottomLeft(), active.bottomRight())

        handle_center_x = int(round(float(track.left()) + float(track.width()) * float(ratio)))
        handle_x = int(handle_center_x - half_handle)
        handle = QRect(int(handle_x), int((self.height() - handle_side) // 2), int(handle_side), int(handle_side))
        _draw_bedrock_frame(painter, handle, fill=thumb_fill, top_left=thumb_light, bottom_right=thumb_dark, outline=QColor("#0b0b0b"))


class WheelPassthroughDoubleSpinBox(QDoubleSpinBox):

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class BedrockToggleSwitch(QAbstractButton):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def sizeHint(self) -> QSize:
        return QSize(74, 40)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def hitButton(self, pos: QPoint) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), self.palette().window())

        frame = QRect(0, 0, 46, 16)
        frame.moveCenter(self.rect().center())
        frame.translate(0, 1)
        if frame.width() <= 0 or frame.height() <= 0:
            return

        checked = bool(self.isChecked())
        enabled = bool(self.isEnabled())
        hovered = bool(self.underMouse())

        if checked:
            frame_fill = QColor("#6FB03A")
            frame_light = QColor("#A9D46A")
            frame_dark = QColor("#254114")
        else:
            frame_fill = QColor("#505050")
            frame_light = QColor("#8C8C8C")
            frame_dark = QColor("#1A1A1A")

        if hovered and enabled:
            frame_fill = frame_fill.lighter(106)

        if not enabled:
            frame_fill.setAlpha(160)
            frame_light.setAlpha(140)
            frame_dark.setAlpha(140)

        _draw_bedrock_frame(painter, frame, fill=frame_fill, top_left=frame_light, bottom_right=frame_dark, outline=QColor("#0b0b0b"))

        thumb_side = 24
        thumb_start_x = frame.left() - 5
        travel = max(0, frame.width() - thumb_side + 10)
        thumb_x = thumb_start_x + (travel if checked else 0)
        thumb = QRect(int(thumb_x), int(frame.center().y() - thumb_side / 2), int(thumb_side), int(thumb_side))

        thumb_fill = QColor("#F5F5F5") if checked else QColor("#E0E0E0")
        thumb_light = QColor("#ffffff")
        thumb_dark = QColor("#5C5C5C")
        if hovered and enabled:
            thumb_fill = thumb_fill.lighter(105)
        if not enabled:
            thumb_fill.setAlpha(180)
            thumb_light.setAlpha(160)
            thumb_dark.setAlpha(160)

        _draw_bedrock_frame(painter, thumb, fill=thumb_fill, top_left=thumb_light, bottom_right=thumb_dark, outline=QColor("#0b0b0b"))


class BedrockToggleRow(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, text: str, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setObjectName("bedrockToggleRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._label = QLabel(str(text), self)
        self._label.setObjectName("bedrockToggleLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._label, stretch=1)

        self._switch = BedrockToggleSwitch(self)
        self._switch.toggled.connect(self.toggled.emit)
        layout.addWidget(self._switch, stretch=0, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.setFocusProxy(self._switch)

    def text(self) -> str:
        return self._label.text()

    def setText(self, text: str) -> None:
        self._label.setText(str(text))

    def isChecked(self) -> bool:
        return bool(self._switch.isChecked())

    def setChecked(self, checked: bool) -> None:
        self._switch.setChecked(bool(checked))

    def sync_checked(self, checked: bool) -> None:
        self._switch.blockSignals(True)
        try:
            self._switch.setChecked(bool(checked))
        finally:
            self._switch.blockSignals(False)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            local_pos = self._switch.mapFromParent(event.position().toPoint())
            if not self._switch.rect().contains(local_pos):
                self._switch.toggle()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if int(event.key()) in (int(Qt.Key.Key_Space), int(Qt.Key.Key_Return), int(Qt.Key.Key_Enter)):
            self._switch.toggle()
            event.accept()
            return
        super().keyPressEvent(event)


class KeybindCaptureButton(QPushButton):
    binding_captured = pyqtSignal(str)
    capture_canceled = pyqtSignal()

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._capturing = False
        self._binding_text = ""
        self.setObjectName("menuBtn")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("Unbound")
        self.clicked.connect(self.begin_capture)

    def binding_text(self) -> str:
        return str(self._binding_text)

    def begin_capture(self) -> None:
        self._capturing = True
        self.setText("Press key...")
        self.setFocus(Qt.FocusReason.MouseFocusReason)

    def sync_binding_text(self, binding_text: str | None) -> None:
        self._binding_text = normalize_binding_text(binding_text)
        if not bool(self._capturing):
            self.setText(display_text_for_binding(self._binding_text))

    def keyPressEvent(self, event) -> None:
        if not bool(self._capturing):
            super().keyPressEvent(event)
            return
        if bool(event.isAutoRepeat()):
            event.accept()
            return
        if int(event.key()) == int(Qt.Key.Key_Escape):
            self._capturing = False
            self.setText(display_text_for_binding(self._binding_text))
            self.capture_canceled.emit()
            event.accept()
            return
        binding_text = normalize_key_code(int(event.key()))
        if binding_text:
            self._capturing = False
            self._binding_text = str(binding_text)
            self.setText(display_text_for_binding(self._binding_text))
            self.binding_captured.emit(str(binding_text))
            event.accept()
            return
        event.accept()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        if bool(self._capturing):
            self._capturing = False
            self.setText(display_text_for_binding(self._binding_text))
            self.capture_canceled.emit()
        super().focusOutEvent(event)


class KeybindRow(QWidget):
    binding_changed = pyqtSignal(str)
    clear_requested = pyqtSignal()

    def __init__(self, text: str, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setObjectName("bedrockToggleRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._label = QLabel(str(text), self)
        self._label.setObjectName("bedrockToggleLabel")
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._label, stretch=1)

        self._button = KeybindCaptureButton(self)
        self._button.setMinimumWidth(132)
        self._button.binding_captured.connect(self.binding_changed.emit)
        layout.addWidget(self._button, stretch=0)

        self._clear_button = QPushButton("Clear", self)
        self._clear_button.setObjectName("menuBtn")
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear_requested.emit)
        layout.addWidget(self._clear_button, stretch=0)

    def sync_binding_text(self, binding_text: str | None) -> None:
        self._button.sync_binding_text(binding_text)
