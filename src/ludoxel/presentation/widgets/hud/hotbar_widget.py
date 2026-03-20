# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QPushButton

from ....shared.domain.blocks.registry.block_registry import BlockRegistry
from ....shared.domain.inventory.hotbar import HOTBAR_SIZE, normalize_hotbar_index, normalize_hotbar_slots
from ..common import ItemPhotoProvider, apply_item_slot_state, hotbar_slot_tooltip

class _DisplaySlot(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("slot")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFixedSize(QSize(46, 46))
        self.setIconSize(QSize(36, 36))
        self.setText("")

    def set_slot_state(self, *, block_id: str | None, tooltip: str, selected: bool, photos: ItemPhotoProvider) -> None:
        bid = "" if block_id is None else str(block_id).strip()
        pixmap = photos.pixmap_for_block(bid) if bid else None
        apply_item_slot_state(self, item_id=bid, tooltip=tooltip, selected=selected, pixmap=pixmap)

class HotbarWidget(QWidget):
    def __init__(self, *, parent: QWidget | None = None, project_root: Path, registry: BlockRegistry) -> None:
        super().__init__(parent)

        self._registry = registry
        self._photos = ItemPhotoProvider(project_root=Path(project_root), registry=registry, icon_size=36)
        self._photos.pixmap_changed.connect(self._on_item_pixmap_changed)
        self._photos.set_active(bool(self.isVisible()))

        self._slots: list[_DisplaySlot] = []
        self._slot_item_ids: list[str] = ["" for _ in range(HOTBAR_SIZE)]

        self.setObjectName("hotbarRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._panel = QFrame(self)
        self._panel.setObjectName("hotbarPanel")
        self._panel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        row = QHBoxLayout(self._panel)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        for _ in range(HOTBAR_SIZE):
            btn = _DisplaySlot(self._panel)
            self._slots.append(btn)
            row.addWidget(btn)

        self.sync_hotbar(slots=normalize_hotbar_slots(None, size=HOTBAR_SIZE), selected_index=0)

    def setVisible(self, visible: bool) -> None:
        super().setVisible(bool(visible))
        self._photos.set_active(bool(visible))

    def set_animations_enabled(self, enabled: bool) -> None:
        self._photos.set_animations_enabled(bool(enabled))

    def sync_hotbar(self, *, slots: tuple[str, ...] | list[str], selected_index: int) -> None:
        norm = normalize_hotbar_slots(slots, size=HOTBAR_SIZE)
        idx = normalize_hotbar_index(selected_index, size=HOTBAR_SIZE)

        for i, btn in enumerate(self._slots):
            bid = str(norm[i]).strip()
            self._slot_item_ids[i] = str(bid)
            btn.set_slot_state(block_id=bid, tooltip=hotbar_slot_tooltip(self._registry, slot_index=i, block_id=bid), selected=(int(i) == int(idx)), photos=self._photos)

        self._panel.adjustSize()
        self.update()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._panel.adjustSize()
        pw = int(self._panel.sizeHint().width())
        ph = int(self._panel.sizeHint().height())
        x = max(0,(int(self.width()) - pw) // 2)
        y = max(0, int(self.height()) - ph - 18)
        self._panel.setGeometry(x, y, pw, ph)

    def _on_item_pixmap_changed(self, block_id: str) -> None:
        normalized = str(block_id).strip()
        if not normalized:
            return
        for index, btn in enumerate(self._slots):
            if str(self._slot_item_ids[index]).strip() != normalized:
                continue
            btn.set_slot_state(block_id=normalized, tooltip=hotbar_slot_tooltip(self._registry, slot_index=index, block_id=normalized), selected=bool(btn.property("selected")), photos=self._photos)