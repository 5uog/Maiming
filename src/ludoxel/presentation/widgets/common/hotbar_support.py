# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from ....application.handlers.keybinds import KeybindSettings, action_for_key, display_text_for_binding, hotbar_action_for_index, hotbar_index_for_action

def refresh_widget_style(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()

def hotbar_index_from_key(key: int, keybinds: KeybindSettings | None=None) -> int | None:
    bindings = keybinds.normalized() if isinstance(keybinds, KeybindSettings) else KeybindSettings()
    action = action_for_key(int(key), bindings)
    return hotbar_index_for_action(action)

def hotbar_binding_text(index: int, keybinds: KeybindSettings | None=None) -> str:
    bindings = keybinds.normalized() if isinstance(keybinds, KeybindSettings) else KeybindSettings()
    action = hotbar_action_for_index(int(index))
    if action is None:
        return ""
    return display_text_for_binding(bindings.binding_for_action(str(action)))