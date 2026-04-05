# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtGui import QColor, QImage

_BASE_SIZE = 16


def build_core_special_item_icon_image(icon_key: str) -> QImage | None:
    image = QImage(_BASE_SIZE, _BASE_SIZE, QImage.Format.Format_RGBA8888)
    image.fill(0)

    normalized = str(icon_key).strip().lower()
    if normalized == "ai_spawn_egg":
        _paint_ai_spawn_icon(image)
    elif normalized == "route_confirm":
        _paint_confirm_icon(image)
    elif normalized == "route_cancel":
        _paint_cancel_icon(image)
    elif normalized == "route_erase":
        _paint_erase_icon(image)
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


def _paint_ai_spawn_icon(image: QImage) -> None:
    _fill_rect(image, "#101010", x=2, y=4, w=1, h=8)
    _fill_rect(image, "#101010", x=3, y=3, w=1, h=1)
    _fill_rect(image, "#101010", x=4, y=2, w=2, h=1)
    _fill_rect(image, "#101010", x=6, y=3, w=1, h=1)
    _fill_rect(image, "#101010", x=7, y=4, w=1, h=8)
    _fill_rect(image, "#101010", x=3, y=7, w=4, h=1)
    _fill_rect(image, "#101010", x=10, y=3, w=4, h=1)
    _fill_rect(image, "#101010", x=11, y=4, w=2, h=8)
    _fill_rect(image, "#101010", x=10, y=12, w=4, h=1)
    _fill_rect(image, "#8cf0b0", x=3, y=4, w=1, h=1)
    _fill_rect(image, "#8cf0b0", x=4, y=3, w=2, h=1)
    _fill_rect(image, "#8cf0b0", x=11, y=4, w=2, h=1)


def _paint_confirm_icon(image: QImage) -> None:
    _set_pixels(image, "#154d16",((3, 8),(3, 9),(4, 9),(4, 10),(5, 10),(5, 11),(6, 9),(6, 10),(7, 8),(7, 9),(8, 7),(8, 8),(9, 6),(9, 7),(10, 5),(10, 6),(11, 4),(11, 5),(12, 3),(12, 4)))
    _set_pixels(image, "#6ee171", ((4, 8), (5, 9), (6, 8), (7, 7), (8, 6), (9, 5), (10, 4), (11, 3)))


def _paint_cancel_icon(image: QImage) -> None:
    dark = "#601010"
    light = "#ff6f6f"
    for index in range(4, 12):
        image.setPixelColor(index, index, QColor(light))
        image.setPixelColor(index, 15 - index, QColor(light))
    for index in range(3, 13):
        image.setPixelColor(index, index - 1 if index > 3 else index, QColor(dark))
        image.setPixelColor(index - 1 if index > 3 else index, index, QColor(dark))
        image.setPixelColor(index, 16 - index if index < 12 else 15 - index, QColor(dark))
        image.setPixelColor(index - 1 if index > 3 else index, 15 - index, QColor(dark))


def _paint_erase_icon(image: QImage) -> None:
    _fill_rect(image, "#cfcfcf", x=5, y=4, w=6, h=2)
    _fill_rect(image, "#cfcfcf", x=4, y=6, w=7, h=3)
    _fill_rect(image, "#d99aa4", x=4, y=9, w=5, h=3)
    _fill_rect(image, "#f6e29f", x=9, y=9, w=3, h=3)
    _set_pixels(image, "#5a5a5a",((5, 4),(6, 4),(7, 4),(8, 4),(9, 4),(10, 4),(4, 6),(10, 6),(4, 7),(10, 7),(4, 8),(10, 8),(4, 9),(11, 9),(4, 10),(11, 10),(4, 11),(11, 11)))
