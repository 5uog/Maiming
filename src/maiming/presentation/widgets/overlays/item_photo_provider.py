# FILE: src/maiming/presentation/widgets/overlays/item_photo_provider.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap

from ....domain.blocks.block_registry import BlockRegistry
from ....domain.inventory.special_items import get_special_item_descriptor
from ....domain.blocks.state_codec import parse_state

@dataclass(frozen=True)
class PhotoPaths:
    project_root: Path

    def thumbs_dir(self) -> Path:
        return self.project_root / "assets" / "minecraft" / "thumbnails" / "blocks"

    def mc_item_dir(self) -> Path:
        return self.project_root / "assets" / "minecraft" / "textures" / "item"

class ItemPhotoProvider:
    def __init__(self, *, project_root: Path, registry: BlockRegistry, icon_size: int = 36) -> None:
        self._root = Path(project_root)
        self._reg = registry
        self._icon = int(max(16, icon_size))
        self._paths = PhotoPaths(project_root=self._root)

        self._pix_cache: dict[str, QPixmap] = {}

    def pixmap_for_block(self, block_state_or_id: str) -> QPixmap | None:
        raw = str(block_state_or_id)
        base_id, _p = parse_state(raw)
        bid = str(base_id)

        if not bid:
            return None

        cached = self._pix_cache.get(bid)
        if cached is not None:
            return cached

        special = get_special_item_descriptor(bid)
        if special is not None:
            pm = self._render_special_item_pixmap(str(special.icon_key))
            self._pix_cache[bid] = pm
            return pm

        defn = self._reg.get(bid)
        if defn is None:
            return None

        name = self._basename_no_ns(bid)

        p = self._paths.thumbs_dir() / f"{name}.png"
        if not p.exists():
            p = self._paths.mc_item_dir() / f"{name}.png"

        if not p.exists():
            return None

        img = QImage(str(p))
        if img.isNull():
            return None

        img = img.convertToFormat(QImage.Format.Format_RGBA8888)
        if img.width() != self._icon or img.height() != self._icon:
            img = img.scaled(self._icon, self._icon, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

        pm = QPixmap.fromImage(img)
        self._pix_cache[bid] = pm
        return pm

    def tooltip_for_block(self, block_id: str) -> str:
        bid = str(block_id)
        special = get_special_item_descriptor(bid)
        if special is not None:
            return f"{special.display_name}\n{special.item_id}"
        d = self._reg.get(bid)
        dn = str(d.display_name) if d is not None else bid
        return f"{dn}\n{bid}"

    @staticmethod
    def _basename_no_ns(block_id: str) -> str:
        s = str(block_id)
        if ":" in s:
            return s.split(":", 1)[1]
        return s

    def _render_special_item_pixmap(self, icon_key: str) -> QPixmap:
        size = int(self._icon)
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        margin = max(2.0, float(size) * 0.08)
        frame_rect = pm.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))

        painter.setPen(QPen(QColor("#0f0f0f"), max(1, size // 18)))
        painter.setBrush(QColor("#2a2a2a"))
        painter.drawRoundedRect(frame_rect, 4.0, 4.0)

        normalized = str(icon_key).strip().lower()
        if normalized == "start":
            self._paint_start_icon(painter, frame_rect)
        else:
            self._paint_settings_icon(painter, frame_rect)

        painter.end()
        return pm

    @staticmethod
    def _paint_start_icon(painter: QPainter, rect) -> None:
        painter.setPen(QPen(QColor("#14360b"), 1))
        painter.setBrush(QColor("#71b442"))

        width = float(rect.width())
        height = float(rect.height())
        left = float(rect.left())
        top = float(rect.top())

        path = QPainterPath()
        path.moveTo(left + width * 0.30, top + height * 0.22)
        path.lineTo(left + width * 0.30, top + height * 0.78)
        path.lineTo(left + width * 0.76, top + height * 0.50)
        path.closeSubpath()
        painter.drawPath(path)

    @staticmethod
    def _paint_settings_icon(painter: QPainter, rect) -> None:
        width = float(rect.width())
        height = float(rect.height())
        left = float(rect.left())
        top = float(rect.top())

        painter.setPen(QPen(QColor("#f1f1f1"), max(2, rect.width() // 12)))
        for row_index, knob_offset in enumerate((0.30, 0.62, 0.44)):
            y = top + height * (0.28 + 0.22 * row_index)
            painter.drawLine(int(left + width * 0.20), int(y), int(left + width * 0.80), int(y))
            painter.setBrush(QColor("#d5d5d5"))
            x = left + width * float(knob_offset)
            radius = max(2.0, width * 0.08)
            painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2.0), int(radius * 2.0))