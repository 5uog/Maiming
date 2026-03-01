# FILE: src/maiming/infrastructure/platform/qt_input_adapter.py
from __future__ import annotations
from dataclasses import dataclass
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QKeyEvent

@dataclass
class InputFrame:
    move_f: float = 0.0
    move_s: float = 0.0

    jump_held: bool = False
    jump_pressed: bool = False

    sprint: bool = False
    crouch: bool = False

    mdx: float = 0.0
    mdy: float = 0.0

class QtInputAdapter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._keys: set[int] = set()

        self._jump_pressed_edge: bool = False

        self._mdx: float = 0.0
        self._mdy: float = 0.0

    def reset(self) -> None:
        self._keys.clear()
        self._jump_pressed_edge = False
        self._mdx = 0.0
        self._mdy = 0.0

    def on_key_press(self, e: QKeyEvent) -> None:
        if bool(e.isAutoRepeat()):
            return
        k = int(e.key())
        self._keys.add(k)
        if k == int(Qt.Key.Key_Space):
            self._jump_pressed_edge = True

    def on_key_release(self, e: QKeyEvent) -> None:
        if bool(e.isAutoRepeat()):
            return
        k = int(e.key())
        if k in self._keys:
            self._keys.remove(k)

    def add_mouse_delta(self, dx: float, dy: float) -> None:
        self._mdx += float(dx)
        self._mdy += float(dy)

    def consume(self) -> InputFrame:
        f = 0.0
        s = 0.0

        if int(Qt.Key.Key_W) in self._keys:
            f += 1.0
        if int(Qt.Key.Key_S) in self._keys:
            f -= 1.0
        if int(Qt.Key.Key_D) in self._keys:
            s += 1.0
        if int(Qt.Key.Key_A) in self._keys:
            s -= 1.0

        crouch = (int(Qt.Key.Key_Shift) in self._keys)
        sprint = (int(Qt.Key.Key_Control) in self._keys)

        jump_held = (int(Qt.Key.Key_Space) in self._keys)
        jump_pressed = bool(self._jump_pressed_edge)

        out = InputFrame(
            move_f=float(f),
            move_s=float(s),
            jump_held=bool(jump_held),
            jump_pressed=bool(jump_pressed),
            sprint=bool(sprint),
            crouch=bool(crouch),
            mdx=float(self._mdx),
            mdy=float(self._mdy),
        )

        self._jump_pressed_edge = False
        self._mdx = 0.0
        self._mdy = 0.0
        return out