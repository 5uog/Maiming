# FILE: src/maiming/infrastructure/rendering/opengl/_internal/resources/texture_atlas.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Iterable
import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QColor
from OpenGL.GL import (
    glGenTextures, glBindTexture, glTexImage2D, glTexParameteri, glDeleteTextures,
    GL_TEXTURE_2D, GL_RGBA, GL_UNSIGNED_BYTE,
    GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_NEAREST,
    GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE,
)

UVRect = Tuple[float, float, float, float]

@dataclass
class TextureAtlas:
    tex_id: int
    uv: Dict[str, UVRect]
    width: int
    height: int

    @staticmethod
    def build_from_dir(
        block_dir: Path,
        tile_size: int = 64,
        names: Iterable[str] | None = None,
        pad: int = 1,
    ) -> "TextureAtlas":
        items = _collect_images(block_dir, tile_size, names=names, pad=pad)

        has_default = any(n == "default" for (n, _img) in items)
        if not has_default:
            items.append(("default", _placeholder(tile_size, QColor(180, 180, 180), pad=pad)))

        n = len(items)
        cols = int(math.ceil(math.sqrt(n)))
        rows = int(math.ceil(n / cols))

        cell = int(tile_size + 2 * max(0, int(pad)))
        w = cols * cell
        h = rows * cell

        atlas = QImage(w, h, QImage.Format.Format_RGBA8888)
        atlas.fill(QColor(0, 0, 0, 0))

        painter = QPainter(atlas)
        uv: Dict[str, UVRect] = {}

        p = int(max(0, int(pad)))

        for i, (name, img) in enumerate(items):
            cx = (i % cols) * cell
            cy = (i // cols) * cell
            painter.drawImage(cx, cy, img)

            u0 = (cx + p) / w
            v0 = (cy + p) / h
            u1 = (cx + p + tile_size) / w
            v1 = (cy + p + tile_size) / h
            uv[name] = (u0, v0, u1, v1)

        painter.end()

        atlas = atlas.convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = atlas.bits()
        ptr.setsize(atlas.sizeInBytes())
        data = bytes(ptr)

        tex_id = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        glBindTexture(GL_TEXTURE_2D, 0)
        return TextureAtlas(tex_id=tex_id, uv=uv, width=w, height=h)

    def destroy(self) -> None:
        if int(self.tex_id) != 0:
            glDeleteTextures(1, [int(self.tex_id)])
            self.tex_id = 0

def _collect_images(block_dir: Path, tile_size: int, names: Iterable[str] | None = None, pad: int = 1) -> list[tuple[str, QImage]]:
    out: list[tuple[str, QImage]] = []
    if not block_dir.exists():
        return out

    p = int(max(0, int(pad)))

    def _prep(img: QImage) -> QImage:
        img = img.convertToFormat(QImage.Format.Format_RGBA8888)
        if img.width() != tile_size or img.height() != tile_size:
            img = img.scaled(
                tile_size,
                tile_size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )

        img = img.mirrored(False, True)

        if p <= 0:
            return img

        return _pad_extrude(img, pad=p)

    if names is None:
        for q in sorted(block_dir.glob("*.png")):
            name = q.stem
            img = QImage(str(q))
            if img.isNull():
                continue
            out.append((name, _prep(img)))
        return out

    for nm in names:
        name = str(nm)
        q = block_dir / f"{name}.png"
        if not q.exists():
            continue
        img = QImage(str(q))
        if img.isNull():
            continue
        out.append((name, _prep(img)))

    return out

def _pad_extrude(src: QImage, pad: int) -> QImage:
    p = int(max(0, pad))
    w = int(src.width())
    h = int(src.height())

    dst = QImage(w + 2 * p, h + 2 * p, QImage.Format.Format_RGBA8888)
    dst.fill(QColor(0, 0, 0, 0))

    painter = QPainter(dst)
    painter.drawImage(p, p, src)

    painter.drawImage(0, p, src.copy(0, 0, 1, h).scaled(p, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
    painter.drawImage(p + w, p, src.copy(w - 1, 0, 1, h).scaled(p, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
    painter.drawImage(p, 0, src.copy(0, 0, w, 1).scaled(w, p, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
    painter.drawImage(p, p + h, src.copy(0, h - 1, w, 1).scaled(w, p, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))

    painter.drawImage(0, 0, src.copy(0, 0, 1, 1).scaled(p, p, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
    painter.drawImage(p + w, 0, src.copy(w - 1, 0, 1, 1).scaled(p, p, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
    painter.drawImage(0, p + h, src.copy(0, h - 1, 1, 1).scaled(p, p, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))
    painter.drawImage(p + w, p + h, src.copy(w - 1, h - 1, 1, 1).scaled(p, p, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation))

    painter.end()
    return dst

def _placeholder(tile: int, c: QColor, pad: int = 1) -> QImage:
    img = QImage(tile, tile, QImage.Format.Format_RGBA8888)
    img.fill(c)
    painter = QPainter(img)
    painter.fillRect(0, 0, tile // 2, tile // 2, QColor(120, 120, 120))
    painter.fillRect(tile // 2, tile // 2, tile // 2, tile // 2, QColor(120, 120, 120))
    painter.end()

    img = img.mirrored(False, True)

    p = int(max(0, int(pad)))
    if p > 0:
        img = _pad_extrude(img, pad=p)
    return img