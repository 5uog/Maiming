# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtGui import QColor, QImage

_BASE_SIZE = 16


def build_othello_special_item_icon_image(icon_key: str) -> QImage | None:
    image = QImage(_BASE_SIZE, _BASE_SIZE, QImage.Format.Format_RGBA8888)
    image.fill(0)

    normalized = str(icon_key).strip().lower()
    if normalized == "start":
        _paint_start_icon(image)
    elif normalized == "settings":
        _paint_settings_icon(image)
    else:
        return None
    return image


def _set_pixels(image: QImage, color: str, pixels: tuple[tuple[int, int], ...]) -> None:
    qcolor = QColor(str(color))
    for x, y in pixels:
        if 0 <= int(x) < int(_BASE_SIZE) and 0 <= int(y) < int(_BASE_SIZE):
            image.setPixelColor(int(x), int(y), qcolor)


def _fill_rect(image: QImage, color: str, *, x: int, y: int, w: int, h: int) -> None:
    pixels = tuple((px, py) for px in range(int(x), int(x) + int(w)) for py in range(int(y), int(y) + int(h)))
    _set_pixels(image, color, pixels)


def _paint_frame(image: QImage, *, fill: str, outline: str, x: int, y: int, w: int, h: int) -> None:
    _fill_rect(image, fill, x=int(x), y=int(y), w=int(w), h=int(h))
    outline_pixels = tuple([(px, int(y)) for px in range(int(x), int(x) + int(w))] + [(px, int(y) + int(h) - 1) for px in range(int(x), int(x) + int(w))] + [(int(x), py) for py in range(int(y), int(y) + int(h))] + [(int(x) + int(w) - 1, py) for py in range(int(y), int(y) + int(h))])
    _set_pixels(image, outline, outline_pixels)


def _paint_start_icon(image: QImage) -> None:
    _paint_frame(image, fill="#2f2f2f", outline="#111111", x=1, y=1, w=14, h=14)
    _set_pixels(image, "#7dd15a",((4, 4),(4, 5),(4, 6),(4, 7),(4, 8),(4, 9),(5, 5),(5, 6),(5, 7),(5, 8),(6, 6),(6, 7),(6, 8),(7, 7),(7, 8),(8, 8),(8, 7),(9, 7),(9, 6),(10, 6),(10, 5),(11, 5),(11, 4)))
    _set_pixels(image, "#c6f29d", ((5, 4), (5, 5), (6, 5), (7, 6), (8, 6), (9, 5), (10, 4)))


def _paint_settings_icon(image: QImage) -> None:
    _paint_frame(image, fill="#2f2f2f", outline="#111111", x=1, y=1, w=14, h=14)
    _fill_rect(image, "#d8d8d8", x=3, y=4, w=10, h=1)
    _fill_rect(image, "#d8d8d8", x=3, y=8, w=10, h=1)
    _fill_rect(image, "#d8d8d8", x=3, y=12, w=10, h=1)
    _fill_rect(image, "#8db7ff", x=5, y=3, w=2, h=3)
    _fill_rect(image, "#8db7ff", x=9, y=7, w=2, h=3)
    _fill_rect(image, "#8db7ff", x=6, y=11, w=2, h=3)
