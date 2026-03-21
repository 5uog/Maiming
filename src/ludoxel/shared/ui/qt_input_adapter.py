# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QKeyEvent

from ...application.runtime.keybinds import ACTION_CROUCH, ACTION_JUMP, ACTION_MOVE_BACKWARD, ACTION_MOVE_FORWARD, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_SPRINT, KeybindSettings

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
        self._keybinds = KeybindSettings()
        self._action_keys: dict[str, int | None] = {}
        self._refresh_action_keys()

        self._jump_pressed_edge: bool = False

        self._mdx: float = 0.0
        self._mdy: float = 0.0

    def _refresh_action_keys(self) -> None:
        bindings = self._keybinds.normalized()
        self._action_keys = {ACTION_MOVE_FORWARD: bindings.key_for_action(ACTION_MOVE_FORWARD), ACTION_MOVE_BACKWARD: bindings.key_for_action(ACTION_MOVE_BACKWARD), ACTION_MOVE_LEFT: bindings.key_for_action(ACTION_MOVE_LEFT), ACTION_MOVE_RIGHT: bindings.key_for_action(ACTION_MOVE_RIGHT), ACTION_JUMP: bindings.key_for_action(ACTION_JUMP), ACTION_CROUCH: bindings.key_for_action(ACTION_CROUCH), ACTION_SPRINT: bindings.key_for_action(ACTION_SPRINT)}

    def set_keybinds(self, keybinds: KeybindSettings) -> None:
        self._keybinds = keybinds.normalized()
        self._refresh_action_keys()

    def _action_pressed(self, action: str) -> bool:
        key = self._action_keys.get(str(action))
        return key is not None and int(key) in self._keys

    def reset(self) -> None:
        self._keys.clear()
        self._jump_pressed_edge = False
        self._mdx = 0.0
        self._mdy = 0.0

    def crouch_held(self) -> bool:
        return self._action_pressed(ACTION_CROUCH)

    def on_key_press(self, e: QKeyEvent) -> None:
        if bool(e.isAutoRepeat()):
            return
        k = int(e.key())
        self._keys.add(k)
        if self._action_keys.get(ACTION_JUMP) == int(k):
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

        if self._action_pressed(ACTION_MOVE_FORWARD):
            f += 1.0
        if self._action_pressed(ACTION_MOVE_BACKWARD):
            f -= 1.0
        if self._action_pressed(ACTION_MOVE_RIGHT):
            s += 1.0
        if self._action_pressed(ACTION_MOVE_LEFT):
            s -= 1.0

        crouch = self._action_pressed(ACTION_CROUCH)
        sprint = self._action_pressed(ACTION_SPRINT)

        jump_held = self._action_pressed(ACTION_JUMP)
        jump_pressed = bool(self._jump_pressed_edge)

        out = InputFrame(move_f=float(f), move_s=float(s), jump_held=bool(jump_held), jump_pressed=bool(jump_pressed), sprint=bool(sprint), crouch=bool(crouch), mdx=float(self._mdx), mdy=float(self._mdy))

        self._jump_pressed_edge = False
        self._mdx = 0.0
        self._mdy = 0.0
        return out