# FILE: src/maiming/presentation/widgets/overlays/item_photo_provider.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from ....domain.blocks.block_registry import BlockRegistry
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
        d = self._reg.get(bid)
        dn = str(d.display_name) if d is not None else bid
        return f"{dn}\n{bid}"

    @staticmethod
    def _basename_no_ns(block_id: str) -> str:
        s = str(block_id)
        if ":" in s:
            return s.split(":", 1)[1]
        return s