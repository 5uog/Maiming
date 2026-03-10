# FILE: src/maiming/presentation/widgets/hud/hotbar_widget.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QPushButton

from ....domain.blocks.block_registry import BlockRegistry
from ..overlays.item_photo_provider import ItemPhotoProvider

def _refresh_widget_style(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()

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

        if bid:
            pm = photos.pixmap_for_block(bid)
            self.setIcon(QIcon(pm) if pm is not None else QIcon())
        else:
            self.setIcon(QIcon())

        self.setToolTip(str(tooltip))
        self.setProperty("selected", bool(selected))
        _refresh_widget_style(self)

class HotbarWidget(QWidget):
    def __init__(self, *, parent: QWidget | None = None, project_root: Path, registry: BlockRegistry) -> None:
        super().__init__(parent)

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

        for _ in range(9):
            btn = _DisplaySlot(self._panel)
            self._slots.append(btn)
            row.addWidget(btn)

        self.sync_hotbar(slots=("", "", "", "", "", "", "", "", ""), selected_index=0)

    @staticmethod
    def _display_name(block_id: str) -> str:
        bid = str(block_id).strip()
        if not bid:
            return "Empty Hand"
        return bid

    def _tooltip_for_slot(self, slot_index: int, block_id: str) -> str:
        bid = str(block_id).strip()
        if not bid:
            return f"Hotbar Slot {int(slot_index) + 1}\nEmpty Hand"
        return f"Hotbar Slot {int(slot_index) + 1}\n{bid}"

    def sync_hotbar(self, *, slots: tuple[str, ...] | list[str], selected_index: int) -> None:
        src = list(slots)
        norm: list[str] = []
        for raw in src[:9]:
            if raw is None:
                norm.append("")
            else:
                norm.append(str(raw).strip())

        while len(norm) < 9:
            norm.append("")

        idx = int(max(0, min(8, int(selected_index))))

        for i, btn in enumerate(self._slots):
            bid = str(norm[i]).strip()
            btn.set_slot_state(
                block_id=bid,
                tooltip=self._tooltip_for_slot(i, bid),
                selected=(int(i) == int(idx)),
                photos=self._photos,
            )

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