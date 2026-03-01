# FILE: src/maiming/presentation/widgets/overlays/inventory_overlay.py
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QGridLayout,
    QScrollArea,
)

from maiming.domain.blocks.block_registry import BlockRegistry
from maiming.domain.blocks.default_registry import create_default_registry
from maiming.presentation.widgets.overlays.item_photo_provider import ItemPhotoProvider

class _SlotButton(QPushButton):
    def __init__(self, block_id: str, display_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._block_id = str(block_id)
        self._display_name = str(display_name)

        self.setObjectName("slot")
        self.setCheckable(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        s = 46
        self.setFixedSize(QSize(s, s))
        self.setIconSize(QSize(36, 36))
        self._set_selected(False)

        self.setToolTip(f"{self._display_name}\n{self._block_id}")

    def block_id(self) -> str:
        return self._block_id

    def set_icon_pixmap(self, pm: QPixmap | None) -> None:
        if pm is None:
            self.setIcon(QIcon())
            return
        self.setIcon(QIcon(pm))

    def _set_selected(self, on: bool) -> None:
        self.setProperty("selected", bool(on))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

class InventoryOverlay(QWidget):
    closed = pyqtSignal()
    block_selected = pyqtSignal(str)

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        project_root: Path,
        registry: BlockRegistry | None = None,
    ) -> None:
        super().__init__(parent)

        self._reg = registry or create_default_registry()
        self._project_root = Path(project_root)
        self._photos = ItemPhotoProvider(project_root=self._project_root, registry=self._reg, icon_size=36)

        self._selected_block_id: str | None = None
        self._slot_buttons: list[_SlotButton] = []

        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("inventoryRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        panel.setMinimumWidth(740)
        panel.setMinimumHeight(520)

        pv = QVBoxLayout(panel)
        pv.setContentsMargins(18, 16, 18, 16)
        pv.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("INVENTORY", panel)
        title.setObjectName("title")
        title_row.addWidget(title)

        title_row.addStretch(1)

        btn_close = QPushButton("Close (E or ESC)", panel)
        btn_close.setObjectName("closeBtn")
        btn_close.clicked.connect(self._close)
        title_row.addWidget(btn_close)
        pv.addLayout(title_row)

        sub = QLabel("Hover a slot to see its display name and minecraft:id. Click to select.", panel)
        sub.setObjectName("subtitle")
        pv.addWidget(sub)

        scroll = QScrollArea(panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_host = QWidget(scroll)
        self._grid_layout = QGridLayout(scroll_host)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(6)
        self._grid_layout.setVerticalSpacing(6)

        scroll.setWidget(scroll_host)
        pv.addWidget(scroll, stretch=1)

        hotbar = QWidget(panel)
        hl = QGridLayout(hotbar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setHorizontalSpacing(6)
        hl.setVerticalSpacing(0)

        self._hotbar_slots: list[QPushButton] = []
        for i in range(9):
            b = QPushButton(hotbar)
            b.setObjectName("slot")
            b.setEnabled(False)
            b.setFixedSize(QSize(46, 46))
            b.setIconSize(QSize(36, 36))
            b.setToolTip("")
            self._hotbar_slots.append(b)
            hl.addWidget(b, 0, i)

        pv.addWidget(hotbar, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        while self._grid_layout.count() > 0:
            item = self._grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        self._slot_buttons.clear()

        blocks = self._reg.all_blocks()
        cols = 12

        for i, b in enumerate(blocks):
            bid = str(b.block_id)
            name = str(b.display_name)
            btn = _SlotButton(bid, name, self)
            btn.clicked.connect(self._on_slot_clicked)

            pm = self._photos.pixmap_for_block(bid)
            btn.set_icon_pixmap(pm)

            self._slot_buttons.append(btn)

            r = i // cols
            c = i % cols
            self._grid_layout.addWidget(btn, r, c)

        self._update_selection_visuals()

    def _set_selected_block(self, block_id: str | None) -> None:
        self._selected_block_id = str(block_id) if block_id is not None else None
        self._update_selection_visuals()

    def _update_selection_visuals(self) -> None:
        sel = self._selected_block_id

        for b in self._slot_buttons:
            b._set_selected(bool(sel is not None and b.block_id() == sel))

        for hb in self._hotbar_slots:
            hb.setIcon(QIcon())
            hb.setProperty("selected", False)
            hb.style().unpolish(hb)
            hb.style().polish(hb)
            hb.update()

        if sel is not None:
            pm = self._photos.pixmap_for_block(sel)
            if pm is not None:
                self._hotbar_slots[0].setIcon(QIcon(pm))
                self._hotbar_slots[0].setProperty("selected", True)
                self._hotbar_slots[0].style().unpolish(self._hotbar_slots[0])
                self._hotbar_slots[0].style().polish(self._hotbar_slots[0])
                self._hotbar_slots[0].update()

    def _on_slot_clicked(self) -> None:
        btn = self.sender()
        if not isinstance(btn, _SlotButton):
            return
        bid = btn.block_id()
        self._set_selected_block(bid)
        self.block_selected.emit(str(bid))
        self._close()

    def _close(self) -> None:
        self.setVisible(False)
        self.closed.emit()

    def keyPressEvent(self, e) -> None:
        k = int(e.key())
        if k == int(Qt.Key.Key_E) or k == int(Qt.Key.Key_Escape):
            self._close()
            return
        super().keyPressEvent(e)