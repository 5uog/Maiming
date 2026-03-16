# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/common/hotbar_support.py
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


def refresh_widget_style(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def hotbar_index_from_key(key: int) -> int | None:
    if key == int(Qt.Key.Key_1):
        return 0
    if key == int(Qt.Key.Key_2):
        return 1
    if key == int(Qt.Key.Key_3):
        return 2
    if key == int(Qt.Key.Key_4):
        return 3
    if key == int(Qt.Key.Key_5):
        return 4
    if key == int(Qt.Key.Key_6):
        return 5
    if key == int(Qt.Key.Key_7):
        return 6
    if key == int(Qt.Key.Key_8):
        return 7
    if key == int(Qt.Key.Key_9):
        return 8
    return None
