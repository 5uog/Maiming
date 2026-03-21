# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QMovie, QPixmap

from ...blocks.registry.block_registry import BlockRegistry
from ....features.othello.domain.inventory.special_items import get_special_item_descriptor
from ....features.othello.ui.special_item_art import build_special_item_icon_image
from ...blocks.state.state_codec import parse_state

@dataclass(frozen=True)
class PhotoPaths:
    project_root: Path

    def thumbs_dir(self) -> Path:
        return self.project_root / "assets" / "minecraft" / "thumbnails" / "blocks"

    def mc_item_dir(self) -> Path:
        return self.project_root / "assets" / "minecraft" / "textures" / "item"

class ItemPhotoProvider(QObject):
    pixmap_changed = pyqtSignal(str)

    def __init__(self, *, project_root: Path, registry: BlockRegistry, icon_size: int = 36) -> None:
        super().__init__(None)
        self._root = Path(project_root)
        self._reg = registry
        self._icon = int(max(16, icon_size))
        self._paths = PhotoPaths(project_root=self._root)
        self._animations_enabled = True
        self._active = False

        self._pix_cache: dict[str, QPixmap] = {}
        self._movies: dict[str, QMovie] = {}
        self._animated_pix_cache: dict[str, QPixmap] = {}

    def set_animations_enabled(self, enabled: bool) -> None:
        next_enabled = bool(enabled)
        if next_enabled == bool(self._animations_enabled):
            return
        self._animations_enabled = bool(next_enabled)
        for block_id, movie in self._movies.items():
            self._sync_movie_playback_state(str(block_id), movie)

    def set_active(self, active: bool) -> None:
        next_active = bool(active)
        if next_active == bool(self._active):
            return
        self._active = bool(next_active)
        for block_id, movie in self._movies.items():
            self._sync_movie_playback_state(str(block_id), movie)

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

        gif_path = self._paths.thumbs_dir() / f"{name}.gif"
        if gif_path.exists():
            return self._ensure_movie_pixmap(str(bid), gif_path)

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

    def _movie_should_run(self) -> bool:
        return bool(self._active) and bool(self._animations_enabled)

    def _render_special_item_pixmap(self, icon_key: str) -> QPixmap:
        return QPixmap.fromImage(build_special_item_icon_image(str(icon_key), size=int(self._icon)))

    def _movie_pixmap(self, movie: QMovie) -> QPixmap | None:
        pixmap = movie.currentPixmap()
        if not pixmap.isNull():
            return QPixmap(pixmap)

        image = movie.currentImage()
        if image.isNull():
            return None

        return QPixmap.fromImage(image)

    def _sync_movie_playback_state(self, block_id: str, movie: QMovie) -> None:
        if self._movie_should_run():
            if movie.state() != QMovie.MovieState.Running:
                movie.start()
            return

        if movie.state() != QMovie.MovieState.NotRunning:
            movie.stop()
        movie.jumpToFrame(0)

        pixmap = self._movie_pixmap(movie)
        if pixmap is None or pixmap.isNull():
            return

        self._animated_pix_cache[str(block_id)] = QPixmap(pixmap)
        self.pixmap_changed.emit(str(block_id))

    def _ensure_movie_pixmap(self, block_id: str, path: Path) -> QPixmap | None:
        cached = self._animated_pix_cache.get(str(block_id))
        if cached is not None and not cached.isNull():
            return cached

        movie = self._movies.get(str(block_id))
        if movie is None:
            movie = QMovie(str(path))
            if not movie.isValid():
                return None
            movie.setScaledSize(QSize(int(self._icon), int(self._icon)))
            movie.frameChanged.connect(lambda _frame, bid=str(block_id), mv=movie: self._on_movie_frame_changed(str(bid), mv))
            self._movies[str(block_id)] = movie

        self._sync_movie_playback_state(str(block_id), movie)

        pixmap = self._movie_pixmap(movie)
        if pixmap is None or pixmap.isNull():
            return None

        self._animated_pix_cache[str(block_id)] = QPixmap(pixmap)
        return self._animated_pix_cache[str(block_id)]

    def _on_movie_frame_changed(self, block_id: str, movie: QMovie) -> None:
        if not self._movie_should_run():
            return
        pixmap = self._movie_pixmap(movie)
        if pixmap is None or pixmap.isNull():
            return
        self._animated_pix_cache[str(block_id)] = QPixmap(pixmap)
        self.pixmap_changed.emit(str(block_id))