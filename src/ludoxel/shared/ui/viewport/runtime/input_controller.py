# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QCursor, QKeyEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from ...qt_input_adapter import InputFrame, QtInputAdapter

@dataclass
class MouseDelta:
    dx: float
    dy: float

class ViewportInput:
    def __init__(self, *, widget: QOpenGLWidget, adapter: QtInputAdapter) -> None:
        self._w = widget
        self._a = adapter
        self._captured: bool = False
        self._capture_sync_pending: bool = False
        self._capture_sync_stable_polls: int = 0

    def reset(self) -> None:
        self._a.reset()

    def captured(self) -> bool:
        return bool(self._captured)

    def capture_sync_pending(self) -> bool:
        return bool(self._captured) and bool(self._capture_sync_pending)

    def crouch_held(self) -> bool:
        return bool(self._a.crouch_held())

    def _center_global(self) -> QPoint:
        c = QPoint(self._w.width() // 2, self._w.height() // 2)
        return self._w.mapToGlobal(c)

    def set_mouse_capture(self, on: bool) -> None:
        on = bool(on)
        if on == self._captured:
            return
        self._captured = on

        if self._captured:
            self._w.setFocus(Qt.FocusReason.MouseFocusReason)
            self._w.setCursor(Qt.CursorShape.BlankCursor)
            self._w.grabMouse()
            self._w.grabKeyboard()
            self._a.clear_mouse_delta()
            QCursor.setPos(self._center_global())
            self._capture_sync_pending = True
            self._capture_sync_stable_polls = 0
        else:
            self._w.releaseKeyboard()
            self._w.releaseMouse()
            self._w.unsetCursor()
            self._capture_sync_pending = False
            self._capture_sync_stable_polls = 0

    def poll_relative_mouse_delta(self) -> None:
        if not bool(self._captured):
            return
        if self.capture_sync_pending():
            center = self._center_global()
            cur = QCursor.pos()
            dx = float(cur.x() - center.x())
            dy = float(cur.y() - center.y())
            self._a.clear_mouse_delta()
            QCursor.setPos(center)
            if abs(float(dx)) <= 1.0 and abs(float(dy)) <= 1.0:
                self._capture_sync_stable_polls = int(self._capture_sync_stable_polls) + 1
            else:
                self._capture_sync_stable_polls = 0
            if int(self._capture_sync_stable_polls) >= 2:
                self._capture_sync_pending = False
                self._capture_sync_stable_polls = 0
            return

        center = self._center_global()
        cur = QCursor.pos()
        dx = float(cur.x() - center.x())
        dy = float(cur.y() - center.y())

        if dx == 0.0 and dy == 0.0:
            return

        self._a.add_mouse_delta(dx, dy)
        QCursor.setPos(center)

    def on_key_press(self, e: QKeyEvent) -> None:
        self._a.on_key_press(e)

    def on_key_release(self, e: QKeyEvent) -> None:
        self._a.on_key_release(e)

    def consume(self, *, invert_x: bool, invert_y: bool) -> tuple[InputFrame, MouseDelta]:
        fr = self._a.consume()
        mdx = float(fr.mdx)
        mdy = float(fr.mdy)

        if bool(invert_x):
            mdx = -mdx
        if bool(invert_y):
            mdy = -mdy

        return fr, MouseDelta(dx=float(mdx), dy=float(mdy))