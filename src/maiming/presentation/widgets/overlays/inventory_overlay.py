# FILE: src/maiming/presentation/widgets/overlays/inventory_overlay.py
from __future__ import annotations
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QByteArray, QMimeData
from PyQt6.QtGui import QPixmap, QIcon, QDrag, QMouseEvent
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy, QGridLayout, QScrollArea

from ....domain.blocks.block_registry import BlockRegistry
from ....domain.inventory.hotbar import HOTBAR_SIZE, normalize_hotbar_index, normalize_hotbar_slots
from ..common import hotbar_index_from_key, refresh_widget_style, hotbar_slot_tooltip
from .item_photo_provider import ItemPhotoProvider

_MIME_BLOCK_ID = "application/x-maiming-block-id"

def _block_id_from_mime(mime: QMimeData) -> str | None:
    if mime.hasFormat(_MIME_BLOCK_ID):
        try:
            raw = bytes(mime.data(_MIME_BLOCK_ID)).decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        bid = str(raw).strip()
        return bid if bid else None

    if mime.hasText():
        bid = str(mime.text()).strip()
        return bid if bid else None

    return None

def _start_block_drag(source: QPushButton, block_id: str) -> None:
    bid = str(block_id).strip()
    if not bid:
        return

    drag = QDrag(source)
    mime = QMimeData()
    mime.setData(_MIME_BLOCK_ID, QByteArray(bid.encode("utf-8")))
    mime.setText(bid)
    drag.setMimeData(mime)

    pm = source.icon().pixmap(source.iconSize())
    if not pm.isNull():
        drag.setPixmap(pm)

    drag.exec(Qt.DropAction.CopyAction)

class _InventoryBlockButton(QPushButton):
    activated = pyqtSignal(str)
    hovered_block = pyqtSignal(str)
    hover_left = pyqtSignal()

    def __init__(self, block_id: str, display_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._block_id = str(block_id)
        self._display_name = str(display_name)
        self._drag_start: QPoint | None = None

        self.setObjectName("slot")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)
        self.setFixedSize(QSize(46, 46))
        self.setIconSize(QSize(36, 36))
        self.setToolTip(f"{self._display_name}\n{self._block_id}")

        self.clicked.connect(lambda: self.activated.emit(str(self._block_id)))

    def block_id(self) -> str:
        return self._block_id

    def set_icon_pixmap(self, pm: QPixmap | None) -> None:
        if pm is None:
            self.setIcon(QIcon())
            return
        self.setIcon(QIcon(pm))

    def enterEvent(self, e) -> None:
        self.hovered_block.emit(str(self._block_id))
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self.hover_left.emit()
        super().leaveEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._drag_start is not None and bool(e.buttons() & Qt.MouseButton.LeftButton):
            if (e.position().toPoint() - self._drag_start).manhattanLength() >= QApplication.startDragDistance():
                self._drag_start = None
                _start_block_drag(self, self._block_id)
                return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(e)

class _HotbarSlotButton(QPushButton):
    slot_selected = pyqtSignal(int)
    block_dropped = pyqtSignal(int, str)

    def __init__(self, slot_index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slot_index = int(slot_index)
        self._block_id = ""
        self._drag_start: QPoint | None = None

        self.setObjectName("slot")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)
        self.setFixedSize(QSize(46, 46))
        self.setIconSize(QSize(36, 36))
        self.setToolTip(f"Hotbar Slot {int(self._slot_index) + 1}\nEmpty Hand")

    def slot_index(self) -> int:
        return int(self._slot_index)

    def block_id(self) -> str:
        return str(self._block_id)

    def set_slot_state(self, *, block_id: str | None, selected: bool, tooltip: str, pixmap: QPixmap | None) -> None:
        bid = "" if block_id is None else str(block_id).strip()
        self._block_id = bid

        if pixmap is None:
            self.setIcon(QIcon())
        else:
            self.setIcon(QIcon(pixmap))

        self.setToolTip(str(tooltip))
        self.setProperty("selected", bool(selected))
        refresh_widget_style(self)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.position().toPoint()
            self.slot_selected.emit(int(self._slot_index))
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if self._drag_start is not None and bool(e.buttons() & Qt.MouseButton.LeftButton):
            if (e.position().toPoint() - self._drag_start).manhattanLength() >= QApplication.startDragDistance():
                self._drag_start = None
                _start_block_drag(self, self._block_id)
                return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(e)

    def dragEnterEvent(self, e) -> None:
        bid = _block_id_from_mime(e.mimeData())
        if bid:
            e.acceptProposedAction()
            return
        e.ignore()

    def dragMoveEvent(self, e) -> None:
        bid = _block_id_from_mime(e.mimeData())
        if bid:
            e.acceptProposedAction()
            return
        e.ignore()

    def dropEvent(self, e) -> None:
        bid = _block_id_from_mime(e.mimeData())
        if not bid:
            e.ignore()
            return

        self.block_dropped.emit(int(self._slot_index), str(bid))
        self.slot_selected.emit(int(self._slot_index))
        e.acceptProposedAction()

class InventoryOverlay(QWidget):
    closed = pyqtSignal()
    block_selected = pyqtSignal(str)
    hotbar_slot_selected = pyqtSignal(int)
    hotbar_slot_assigned = pyqtSignal(int, str)

    def __init__(self, *, parent: QWidget | None = None, project_root: Path, registry: BlockRegistry) -> None:
        super().__init__(parent)

        self._reg = registry
        self._project_root = Path(project_root)
        self._photos = ItemPhotoProvider(project_root=self._project_root, registry=self._reg, icon_size=36)

        self._hovered_block_id: str | None = None
        self._hotbar_slots: list[str] = list(normalize_hotbar_slots(None, size=HOTBAR_SIZE))
        self._selected_hotbar_index: int = 0
        self._creative_mode: bool = False

        self._slot_buttons: list[_InventoryBlockButton] = []
        self._hotbar_buttons: list[_HotbarSlotButton] = []

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
        self._title_label = QLabel("INVENTORY", panel)
        self._title_label.setObjectName("title")
        title_row.addWidget(self._title_label)

        title_row.addStretch(1)

        btn_close = QPushButton("Close (E or ESC)", panel)
        btn_close.setObjectName("closeBtn")
        btn_close.clicked.connect(self._close)
        title_row.addWidget(btn_close)
        pv.addLayout(title_row)

        self._subtitle_label = QLabel("Click assigns the hovered block to the currently selected hotbar slot. Drag blocks onto any hotbar slot, or hover a block and press 1-9.", panel)
        self._subtitle_label.setObjectName("subtitle")
        self._subtitle_label.setWordWrap(True)
        pv.addWidget(self._subtitle_label)

        self._catalog_scroll = QScrollArea(panel)
        self._catalog_scroll.setWidgetResizable(True)
        self._catalog_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_host = QWidget(self._catalog_scroll)
        self._grid_layout = QGridLayout(scroll_host)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(6)
        self._grid_layout.setVerticalSpacing(6)

        self._catalog_scroll.setWidget(scroll_host)
        pv.addWidget(self._catalog_scroll, stretch=1)

        hotbar = QWidget(panel)
        hl = QGridLayout(hotbar)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setHorizontalSpacing(6)
        hl.setVerticalSpacing(0)

        for i in range(HOTBAR_SIZE):
            b = _HotbarSlotButton(i, hotbar)
            b.slot_selected.connect(self._on_hotbar_slot_selected)
            b.block_dropped.connect(self._on_hotbar_slot_dropped)
            self._hotbar_buttons.append(b)
            hl.addWidget(b, 0, i)

        pv.addWidget(hotbar, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)

        self._rebuild_grid()
        self.set_creative_mode(False)
        self.sync_hotbar(slots=self._hotbar_slots, selected_index=self._selected_hotbar_index)

    def set_creative_mode(self, on: bool) -> None:
        self._creative_mode = bool(on)

        if bool(self._creative_mode):
            self._title_label.setText("CREATIVE INVENTORY")
            self._subtitle_label.setText("Click assigns the hovered block to the currently selected hotbar slot. Drag blocks onto any hotbar slot, or hover a block and press 1-9.")
            self._catalog_scroll.setVisible(True)
            return

        self._hovered_block_id = None
        self._title_label.setText("SURVIVAL INVENTORY")
        self._subtitle_label.setText("Creative block selection is unavailable in Survival Mode. Use 1-9 to select a hotbar slot, or drag between hotbar slots.")
        self._catalog_scroll.setVisible(False)

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

            btn = _InventoryBlockButton(bid, name, self)
            btn.activated.connect(self._on_block_activated)
            btn.hovered_block.connect(self._on_block_hovered)
            btn.hover_left.connect(self._on_block_hover_left)
            btn.set_icon_pixmap(self._photos.pixmap_for_block(bid))

            self._slot_buttons.append(btn)

            r = i // cols
            c = i % cols
            self._grid_layout.addWidget(btn, r, c)

    def _sync_hotbar_buttons(self) -> None:
        for i, btn in enumerate(self._hotbar_buttons):
            bid = str(self._hotbar_slots[i]).strip()
            pm = self._photos.pixmap_for_block(bid) if bid else None
            btn.set_slot_state(block_id=bid, selected=(int(i) == int(self._selected_hotbar_index)), tooltip=hotbar_slot_tooltip(self._reg, slot_index=i, block_id=bid), pixmap=pm)

    def sync_hotbar(self, *, slots: tuple[str, ...] | list[str], selected_index: int) -> None:
        norm = normalize_hotbar_slots(slots, size=HOTBAR_SIZE)
        idx = normalize_hotbar_index(selected_index, size=HOTBAR_SIZE)

        self._hotbar_slots = list(norm)
        self._selected_hotbar_index = int(idx)
        self._sync_hotbar_buttons()

    def _on_block_hovered(self, block_id: str) -> None:
        self._hovered_block_id = str(block_id).strip()

    def _on_block_hover_left(self) -> None:
        self._hovered_block_id = None

    def _on_block_activated(self, block_id: str) -> None:
        if not bool(self._creative_mode):
            return
        self.block_selected.emit(str(block_id))
        self._close()

    def _on_hotbar_slot_selected(self, slot_index: int) -> None:
        self.hotbar_slot_selected.emit(int(slot_index))

    def _on_hotbar_slot_dropped(self, slot_index: int, block_id: str) -> None:
        self.hotbar_slot_assigned.emit(int(slot_index), str(block_id))

    def _close(self) -> None:
        self._hovered_block_id = None
        self.setVisible(False)
        self.closed.emit()

    def keyPressEvent(self, e) -> None:
        k = int(e.key())

        if k == int(Qt.Key.Key_E) or k == int(Qt.Key.Key_Escape):
            self._close()
            return

        idx = hotbar_index_from_key(k)
        if idx is not None:
            self.hotbar_slot_selected.emit(int(idx))
            if bool(self._creative_mode) and self._hovered_block_id is not None:
                self.hotbar_slot_assigned.emit(int(idx), str(self._hovered_block_id))
            return

        super().keyPressEvent(e)