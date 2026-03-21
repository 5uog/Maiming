# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtGui import QImage

from OpenGL.GL import glBindTexture, glDeleteTextures, glTexParameteri, glGenTextures, glTexImage2D, GL_CLAMP_TO_EDGE, GL_NEAREST, GL_RGBA, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_UNSIGNED_BYTE

@dataclass
class ImageTexture:
    tex_id: int
    width: int
    height: int

    @staticmethod
    def from_image(image: QImage) -> "ImageTexture":
        img = QImage(image)
        if img.isNull():
            raise RuntimeError("Unable to upload texture image because the source image is null.")

        img = img.convertToFormat(QImage.Format.Format_RGBA8888).mirrored(False, True)
        ptr = img.bits()
        ptr.setsize(img.sizeInBytes())
        data = bytes(ptr)

        tex_id = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, int(img.width()), int(img.height()), 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)

        return ImageTexture(tex_id=tex_id, width=int(img.width()), height=int(img.height()))

    @staticmethod
    def load(path: Path) -> "ImageTexture":
        img = QImage(str(path))
        if img.isNull():
            raise RuntimeError(f"Unable to load texture image: {path}")
        return ImageTexture.from_image(img)

    def destroy(self) -> None:
        if int(self.tex_id) != 0:
            glDeleteTextures(1,[int(self.tex_id)])
            self.tex_id = 0