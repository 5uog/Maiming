# FILE: src/maiming/presentation/widgets/hud/hotbar_widget.py
from __future__ import annotations
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QPushButton

from ....domain.blocks.block_registry import BlockRegistry
from ....domain.inventory.hotbar import HOTBAR_SIZE, normalize_hotbar_index, normalize_hotbar_slots
from ..common import apply_item_slot_state, hotbar_slot_tooltip
from ..overlays.item_photo_provider import ItemPhotoProvider

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
        self._slots: list[_DisplaySlot] = []

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

    def sync_hotbar(self, *, slots: tuple[str, ...] | list[str], selected_index: int) -> None:
        norm = normalize_hotbar_slots(slots, size=HOTBAR_SIZE)
        idx = normalize_hotbar_index(selected_index, size=HOTBAR_SIZE)

        for i, btn in enumerate(self._slots):
            bid = str(norm[i]).strip()
            btn.set_slot_state(block_id=bid, tooltip=hotbar_slot_tooltip(self._registry, slot_index=i, block_id=bid), selected=(int(i) == int(idx)), photos=self._photos)

        self._panel.adjustSize()
        self.update()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._panel.adjustSize()
        pw = int(self._panel.sizeHint().width())
        ph = int(self._panel.sizeHint().height())
        x = max(0, (int(self.width()) - pw) // 2)
        y = max(0, int(self.height()) - ph - 18)
        self._panel.setGeometry(x, y, pw, ph)