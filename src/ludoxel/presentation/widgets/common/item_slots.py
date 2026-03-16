# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/common/item_slots.py
from __future__ import annotations

from PyQt6.QtCore import QByteArray, QMimeData, QPoint, Qt
from PyQt6.QtGui import QDrag, QIcon, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QPushButton

from .hotbar_support import refresh_widget_style

ITEM_SLOT_MIME_TYPE = "application/x-ludoxel-block-id"


def item_id_from_mime(mime: QMimeData) -> str | None:
    if mime.hasFormat(ITEM_SLOT_MIME_TYPE):
        try:
            raw = bytes(mime.data(ITEM_SLOT_MIME_TYPE)).decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        item_id = str(raw).strip()
        return item_id if item_id else None
    if mime.hasText():
        item_id = str(mime.text()).strip()
        return item_id if item_id else None
    return None


def start_item_drag(source: QPushButton, item_id: str) -> None:
    normalized = str(item_id).strip()
    if not normalized:
        return

    drag = QDrag(source)
    mime = QMimeData()
    mime.setData(ITEM_SLOT_MIME_TYPE, QByteArray(normalized.encode("utf-8")))
    mime.setText(normalized)
    drag.setMimeData(mime)

    pixmap = source.icon().pixmap(source.iconSize())
    if not pixmap.isNull():
        drag.setPixmap(pixmap)

    drag.exec(Qt.DropAction.CopyAction)


def apply_item_slot_state(button: QPushButton, *, item_id: str | None, tooltip: str, selected: bool, pixmap: QPixmap | None) -> None:
    normalized_item_id = "" if item_id is None else str(item_id).strip()

    if pixmap is None:
        button.setIcon(QIcon())
    else:
        button.setIcon(QIcon(pixmap))

    button.setToolTip(str(tooltip))
    button.setProperty("itemId", normalized_item_id)
    button.setProperty("selected", bool(selected))
    refresh_widget_style(button)


class DraggableItemButton(QPushButton):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drag_item_id = ""
        self._drag_start: QPoint | None = None

    def set_drag_item_id(self, item_id: str | None) -> None:
        self._drag_item_id = "" if item_id is None else str(item_id).strip()

    def drag_item_id(self) -> str:
        return str(self._drag_item_id)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._drag_start is not None and bool(e.buttons() & Qt.MouseButton.LeftButton):
            if (e.position().toPoint() - self._drag_start).manhattanLength() >= QApplication.startDragDistance():
                self._drag_start = None
                start_item_drag(self, self._drag_item_id)
                return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(e)
