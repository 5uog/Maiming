# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable

from PyQt6.QtGui import QKeySequence

ACTION_MOVE_FORWARD = "move_forward"
ACTION_MOVE_BACKWARD = "move_backward"
ACTION_MOVE_LEFT = "move_left"
ACTION_MOVE_RIGHT = "move_right"
ACTION_JUMP = "jump"
ACTION_CROUCH = "crouch"
ACTION_SPRINT = "sprint"
ACTION_TOGGLE_INVENTORY = "toggle_inventory"
ACTION_TOGGLE_CREATIVE_MODE = "toggle_creative_mode"
ACTION_TOGGLE_DEBUG_HUD = "toggle_debug_hud"
ACTION_TOGGLE_DEBUG_SHADOW = "toggle_debug_shadow"
ACTION_CLEAR_SELECTED_SLOT = "clear_selected_slot"

HOTBAR_ACTIONS: tuple[str, ...] = tuple(f"hotbar_slot_{int(index) + 1}" for index in range(9))

KEYBIND_ACTION_ORDER: tuple[str, ...] = (ACTION_MOVE_FORWARD, ACTION_MOVE_BACKWARD, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_JUMP, ACTION_CROUCH, ACTION_SPRINT, ACTION_TOGGLE_INVENTORY, ACTION_TOGGLE_CREATIVE_MODE, ACTION_TOGGLE_DEBUG_HUD, ACTION_TOGGLE_DEBUG_SHADOW, ACTION_CLEAR_SELECTED_SLOT) + HOTBAR_ACTIONS

KEYBIND_DISPLAY_NAMES: dict[str, str] = {ACTION_MOVE_FORWARD: "Move Forward", ACTION_MOVE_BACKWARD: "Move Backward", ACTION_MOVE_LEFT: "Move Left", ACTION_MOVE_RIGHT: "Move Right", ACTION_JUMP: "Jump", ACTION_CROUCH: "Crouch", ACTION_SPRINT: "Sprint", ACTION_TOGGLE_INVENTORY: "Inventory", ACTION_TOGGLE_CREATIVE_MODE: "Creative Mode", ACTION_TOGGLE_DEBUG_HUD: "Debug HUD", ACTION_TOGGLE_DEBUG_SHADOW: "Debug Shadow", ACTION_CLEAR_SELECTED_SLOT: "Clear Selected Slot"}
for _index, _action in enumerate(HOTBAR_ACTIONS, start=1):
    KEYBIND_DISPLAY_NAMES[_action] = f"Hotbar Slot {int(_index)}"

CONTROL_SECTION_MOVEMENT: tuple[str, ...] = (ACTION_MOVE_FORWARD, ACTION_MOVE_BACKWARD, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_JUMP, ACTION_CROUCH, ACTION_SPRINT)
CONTROL_SECTION_GAMEPLAY: tuple[str, ...] = (ACTION_TOGGLE_INVENTORY, ACTION_TOGGLE_CREATIVE_MODE, ACTION_CLEAR_SELECTED_SLOT, ACTION_TOGGLE_DEBUG_HUD, ACTION_TOGGLE_DEBUG_SHADOW)

DEFAULT_KEYBINDS: dict[str, str] = {ACTION_MOVE_FORWARD: "W", ACTION_MOVE_BACKWARD: "S", ACTION_MOVE_LEFT: "A", ACTION_MOVE_RIGHT: "D", ACTION_JUMP: "Space", ACTION_CROUCH: "Shift", ACTION_SPRINT: "Control", ACTION_TOGGLE_INVENTORY: "E", ACTION_TOGGLE_CREATIVE_MODE: "B", ACTION_TOGGLE_DEBUG_HUD: "F3", ACTION_TOGGLE_DEBUG_SHADOW: "F4", ACTION_CLEAR_SELECTED_SLOT: "Q"}
for _index, _action in enumerate(HOTBAR_ACTIONS, start=1):
    DEFAULT_KEYBINDS[_action] = str(int(_index))

def keybind_actions() -> tuple[str, ...]:
    return KEYBIND_ACTION_ORDER

def default_keybinds_map() -> dict[str, str]:
    return dict(DEFAULT_KEYBINDS)

def action_display_name(action: str) -> str:
    normalized = str(action).strip()
    return str(KEYBIND_DISPLAY_NAMES.get(normalized, normalized))

def hotbar_action_for_index(index: int) -> str | None:
    idx = int(index)
    if 0 <= idx < len(HOTBAR_ACTIONS):
        return str(HOTBAR_ACTIONS[idx])
    return None

def hotbar_index_for_action(action: str | None) -> int | None:
    normalized = "" if action is None else str(action).strip()
    for index, candidate in enumerate(HOTBAR_ACTIONS):
        if normalized == str(candidate):
            return int(index)
    return None

@lru_cache(maxsize=256)
def portable_text_for_key(key: int) -> str:
    sequence = QKeySequence(int(key))
    return str(sequence.toString(QKeySequence.SequenceFormat.PortableText)).strip()

def normalize_key_code(key: int) -> str:
    try:
        normalized_key = int(key)
    except Exception:
        return ""
    if normalized_key <= 0:
        return ""
    return portable_text_for_key(int(normalized_key))

@lru_cache(maxsize=512)
def _normalize_binding_text_cached(raw: str) -> str:
    source = str(raw).strip()
    if not source:
        return ""

    sequence = QKeySequence.fromString(source, QKeySequence.SequenceFormat.PortableText)
    if sequence.count() <= 0:
        return ""

    combination = sequence[0]
    if int(combination.keyboardModifiers().value) != 0:
        return ""

    try:
        key = int(combination.key())
    except Exception:
        return ""

    if key <= 0:
        return ""
    return portable_text_for_key(int(key))

def normalize_binding_text(value: object) -> str:
    return _normalize_binding_text_cached(str(value))

@lru_cache(maxsize=512)
def _binding_to_key_cached(normalized_binding: str) -> int | None:
    if not normalized_binding:
        return None

    sequence = QKeySequence.fromString(str(normalized_binding), QKeySequence.SequenceFormat.PortableText)
    if sequence.count() <= 0:
        return None

    combination = sequence[0]
    if int(combination.keyboardModifiers().value) != 0:
        return None

    try:
        key = int(combination.key())
    except Exception:
        return None
    return key if key > 0 else None

def binding_to_key(binding: str | None) -> int | None:
    normalized = normalize_binding_text("" if binding is None else binding)
    return _binding_to_key_cached(str(normalized))

@lru_cache(maxsize=512)
def _display_text_for_binding_cached(normalized_binding: str) -> str:
    if not normalized_binding:
        return "Unbound"

    sequence = QKeySequence.fromString(str(normalized_binding), QKeySequence.SequenceFormat.PortableText)
    if sequence.count() <= 0:
        return "Unbound"

    native = str(sequence.toString(QKeySequence.SequenceFormat.NativeText)).strip()
    return native or str(normalized_binding)

def display_text_for_binding(binding: str | None) -> str:
    normalized = normalize_binding_text("" if binding is None else binding)
    return _display_text_for_binding_cached(str(normalized))

def _normalized_bindings_from_items(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    normalized = {str(action): "" for action in KEYBIND_ACTION_ORDER}
    seen_by_binding: dict[str, str] = {}

    for action, binding in items:
        normalized_action = str(action).strip()
        if normalized_action not in normalized:
            continue

        normalized_binding = normalize_binding_text(binding)
        if normalized_binding:
            previous_action = seen_by_binding.get(str(normalized_binding))
            if previous_action is not None and previous_action in normalized:
                normalized[str(previous_action)] = ""
            seen_by_binding[str(normalized_binding)] = str(normalized_action)

        normalized[str(normalized_action)] = str(normalized_binding)

    return normalized

def _key_maps_for_bindings(bindings: dict[str, str]) -> tuple[dict[str, int | None], dict[int, str]]:
    keys_by_action: dict[str, int | None] = {}
    action_by_key: dict[int, str] = {}

    for action in KEYBIND_ACTION_ORDER:
        key = binding_to_key(bindings.get(str(action), ""))
        keys_by_action[str(action)] = key
        if key is not None:
            action_by_key[int(key)] = str(action)

    return keys_by_action, action_by_key

@dataclass(frozen=True)
class KeybindSettings:
    bindings: dict[str, str] = field(default_factory=default_keybinds_map)
    _keys_by_action: dict[str, int | None] = field(init=False, repr=False, compare=False)
    _action_by_key: dict[int, str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        seeded = default_keybinds_map()
        for action, value in dict(self.bindings).items():
            normalized_action = str(action).strip()
            if normalized_action not in seeded:
                continue
            seeded[normalized_action] = "" if value is None else str(value)

        canonical = _normalized_bindings_from_items((str(action), str(seeded.get(str(action), ""))) for action in KEYBIND_ACTION_ORDER)
        object.__setattr__(self, "bindings", canonical)

        keys_by_action, action_by_key = _key_maps_for_bindings(canonical)
        object.__setattr__(self, "_keys_by_action", keys_by_action)
        object.__setattr__(self, "_action_by_key", action_by_key)

    def normalized(self) -> "KeybindSettings":
        return self

    def binding_for_action(self, action: str) -> str:
        return str(self.bindings.get(str(action).strip(), ""))

    def key_for_action(self, action: str) -> int | None:
        return self._keys_by_action.get(str(action).strip())

    def action_for_key_code(self, key: int) -> str | None:
        try:
            normalized_key = int(key)
        except Exception:
            return None
        return self._action_by_key.get(int(normalized_key))

    def display_text_for_action(self, action: str) -> str:
        return display_text_for_binding(self.binding_for_action(str(action)))

    def with_binding(self, action: str, binding: str | None) -> "KeybindSettings":
        normalized_action = str(action).strip()
        if normalized_action not in self.bindings:
            return self

        updated = dict(self.bindings)
        updated[normalized_action] = normalize_binding_text("" if binding is None else binding)
        return KeybindSettings(bindings=updated)

    def to_dict(self) -> dict[str, str]:
        return {str(action): str(self.bindings.get(str(action), "")) for action in KEYBIND_ACTION_ORDER}

    @staticmethod
    def from_dict(data: object) -> "KeybindSettings":
        seeded = default_keybinds_map()
        if isinstance(data, dict):
            for action in KEYBIND_ACTION_ORDER:
                if action in data:
                    seeded[str(action)] = "" if data[action] is None else str(data[action])
        return KeybindSettings(bindings=seeded)

def action_for_key(key: int, bindings: "KeybindSettings") -> str | None:
    return bindings.normalized().action_for_key_code(int(key))