# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import math

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QPushButton

from ...blocks.registry.block_registry import BlockRegistry
from ...math.scalars import clampf
from ...world.inventory.hotbar import HOTBAR_SIZE, normalize_hotbar_index, normalize_hotbar_slots
from ..common import ItemPhotoProvider, apply_item_slot_state, hotbar_slot_tooltip


class _DisplaySlot(QPushButton):

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self.setObjectName("slot")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFixedSize(QSize(46, 46))
        self.setIconSize(QSize(36, 36))
        self.setText("")

    def set_slot_state(self, *, item_id: str | None, tooltip: str, selected: bool, photos: ItemPhotoProvider) -> None:
        normalized_item_id = "" if item_id is None else str(item_id).strip()
        pixmap = photos.pixmap_for_item(normalized_item_id) if normalized_item_id else None
        apply_item_slot_state(self, item_id=normalized_item_id, tooltip=tooltip, selected=selected, pixmap=pixmap)


class _HealthStrip(QWidget):

    _HEART_MASK: tuple[str, ...] = ("01100110", "11111111", "11111111", "01111110", "00111100", "00011000", "00000000")

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)
        self._show_health = False
        self._health = 20.0
        self._max_health = 20.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_state(self, *, show_health: bool, health: float, max_health: float) -> None:
        self._show_health = bool(show_health)
        self._max_health = max(2.0, float(max_health))
        self._health = max(0.0, min(float(health), float(self._max_health)))
        self.setVisible(bool(self._show_health))
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(420, 18)

    def paintEvent(self, event) -> None:
        del event
        if not bool(self._show_health):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        heart_count = max(1, int(math.ceil(float(self._max_health) * 0.5)))
        pattern_height = len(self._HEART_MASK)
        pattern_width = len(self._HEART_MASK[0])
        gap_units = 1
        scale_w = max(1, int(self.width()) // max(1, heart_count * pattern_width + (heart_count - 1) * gap_units))
        scale_h = max(1, int(self.height()) // max(1, pattern_height))
        scale = max(1, min(2, scale_w, scale_h))
        heart_width = pattern_width * scale
        heart_height = pattern_height * scale
        gap = gap_units * scale
        start_x = 0
        top = max(0, (int(self.height()) - heart_height) // 2)
        filled_hearts = float(self._health) * 0.5

        for index in range(int(heart_count)):
            x = int(start_x) + int(index) * (int(heart_width) + int(gap))
            self._paint_pixel_heart(painter, x=int(x), y=int(top), scale=int(scale), fill_ratio=clampf(float(filled_hearts) - float(index), 0.0, 1.0))

        painter.end()

    def _paint_pixel_heart(self, painter: QPainter, *, x: int, y: int, scale: int, fill_ratio: float) -> None:
        fill_limit_x = int(round(float(x) + float(len(self._HEART_MASK[0]) * scale) * float(fill_ratio)))
        for row_index, row in enumerate(self._HEART_MASK):
            for col_index, value in enumerate(row):
                if value != "1":
                    continue
                px = int(x) + int(col_index) * int(scale)
                py = int(y) + int(row_index) * int(scale)
                painter.fillRect(px, py, int(scale), int(scale), QColor("#19090a"))
                if int(px + scale) <= int(fill_limit_x):
                    painter.fillRect(px, py, int(scale), int(scale), QColor("#cc2e43"))
                elif int(px) < int(fill_limit_x):
                    painter.fillRect(px, py, int(fill_limit_x) - int(px), int(scale), QColor("#cc2e43"))
                if row_index <= 1 and int(px + scale) <= int(fill_limit_x):
                    painter.fillRect(px, py, int(scale), 1, QColor("#ff8e8f"))


class HotbarWidget(QWidget):

    def __init__(self, *, parent: QWidget | None=None, resource_root: Path, registry: BlockRegistry) -> None:
        super().__init__(parent)

        self._registry = registry
        self._photos = ItemPhotoProvider(resource_root=Path(resource_root), registry=registry, icon_size=36)
        self._photos.pixmap_changed.connect(self._on_item_pixmap_changed)
        self._photos.set_active(bool(self.isVisible()))

        self._slots: list[_DisplaySlot] = []
        self._slot_item_ids: list[str] = ["" for _ in range(HOTBAR_SIZE)]
        self._show_health: bool = False
        self._health: float = 20.0
        self._max_health: float = 20.0

        self.setObjectName("hotbarRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._panel = QFrame(self)
        self._panel.setObjectName("hotbarPanel")
        self._panel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._health_strip = _HealthStrip(self)
        self._health_strip.setVisible(False)

        row = QHBoxLayout(self._panel)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        for _ in range(HOTBAR_SIZE):
            btn = _DisplaySlot(self._panel)
            self._slots.append(btn)
            row.addWidget(btn)

        self.sync_hotbar(slots=normalize_hotbar_slots(None, size=HOTBAR_SIZE), selected_index=0)
        self.set_status(show_health=False, health=20.0, max_health=20.0)

    def setVisible(self, visible: bool) -> None:
        super().setVisible(bool(visible))
        self._photos.set_active(bool(visible))

    def set_animations_enabled(self, enabled: bool) -> None:
        self._photos.set_animations_enabled(bool(enabled))

    def set_status(self, *, show_health: bool, health: float, max_health: float) -> None:
        self._show_health = bool(show_health)
        self._health = float(health)
        self._max_health = float(max_health)
        self._health_strip.set_state(show_health=bool(self._show_health), health=float(self._health), max_health=float(self._max_health))
        self._layout_children()

    def sync_hotbar(self, *, slots: tuple[str, ...] | list[str], selected_index: int) -> None:
        norm = normalize_hotbar_slots(slots, size=HOTBAR_SIZE)
        idx = normalize_hotbar_index(selected_index, size=HOTBAR_SIZE)

        for i, btn in enumerate(self._slots):
            item_id = str(norm[i]).strip()
            self._slot_item_ids[i] = str(item_id)
            btn.set_slot_state(item_id=item_id, tooltip=hotbar_slot_tooltip(self._registry, slot_index=i, item_id=item_id), selected=(int(i) == int(idx)), photos=self._photos)

        self._panel.adjustSize()
        self._layout_children()
        self.update()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._panel.adjustSize()
        self._layout_children()

    def _layout_children(self) -> None:
        pw = int(self._panel.sizeHint().width())
        ph = int(self._panel.sizeHint().height())
        x = max(0, (int(self.width()) - pw) // 2)
        y = max(0, int(self.height()) - ph - 18)
        self._panel.setGeometry(x, y, pw, ph)

        hh = int(self._health_strip.sizeHint().height())
        hy = max(0, int(y) - hh - 8)
        self._health_strip.setGeometry(int(x), int(hy), int(pw), int(hh))

    def _on_item_pixmap_changed(self, item_id: str) -> None:
        normalized = str(item_id).strip()
        if not normalized:
            return
        for index, btn in enumerate(self._slots):
            if str(self._slot_item_ids[index]).strip() != normalized:
                continue
            btn.set_slot_state(item_id=normalized, tooltip=hotbar_slot_tooltip(self._registry, slot_index=index, item_id=normalized), selected=bool(btn.property("selected")), photos=self._photos)
