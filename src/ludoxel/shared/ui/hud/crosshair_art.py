# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtGui import QColor, QImage

CROSSHAIR_GRID_SIZE = 16

CROSSHAIR_MODE_DEFAULT = "default"
CROSSHAIR_MODE_CUSTOM = "custom"

_EMPTY_ROW = "0" * CROSSHAIR_GRID_SIZE

DEFAULT_CROSSHAIR_PIXELS: tuple[str, ...] = (_EMPTY_ROW, _EMPTY_ROW, "0000000100000000", "0000000100000000", "0000000100000000", "0000000100000000", "0000000100000000", "0011111111111000", "0000000100000000", "0000000100000000", "0000000100000000", "0000000100000000", "0000000100000000", _EMPTY_ROW, _EMPTY_ROW, _EMPTY_ROW)
EMPTY_CROSSHAIR_PIXELS: tuple[str, ...] = tuple(_EMPTY_ROW for _ in range(CROSSHAIR_GRID_SIZE))

def normalize_crosshair_mode(value: object) -> str:
    if str(value or "").strip().lower() == CROSSHAIR_MODE_CUSTOM:
        return CROSSHAIR_MODE_CUSTOM
    return CROSSHAIR_MODE_DEFAULT

def normalize_crosshair_pixels(value: object) -> tuple[str, ...]:
    rows: list[str] = []
    if isinstance(value, (list, tuple)):
        for raw_row in value[:CROSSHAIR_GRID_SIZE]:
            text = str(raw_row or "")
            row = "".join("1" if ch == "1" else "0" for ch in text[:CROSSHAIR_GRID_SIZE])
            row = row.ljust(CROSSHAIR_GRID_SIZE, "0")
            rows.append(row)
    while len(rows) < CROSSHAIR_GRID_SIZE:
        rows.append(_EMPTY_ROW)
    return tuple(rows[:CROSSHAIR_GRID_SIZE])

def active_crosshair_pixels(mode: object, custom_pixels: object) -> tuple[str, ...]:
    if normalize_crosshair_mode(mode) == CROSSHAIR_MODE_CUSTOM:
        return normalize_crosshair_pixels(custom_pixels)
    return DEFAULT_CROSSHAIR_PIXELS

def render_crosshair_image(mode: object, custom_pixels: object, *, scale: int = 2, fill: QColor | None = None, outline: QColor | None = None) -> QImage:
    pixels = active_crosshair_pixels(mode, custom_pixels)
    pixel_scale = max(1, int(scale))
    image = QImage(int(CROSSHAIR_GRID_SIZE) * pixel_scale, int(CROSSHAIR_GRID_SIZE) * pixel_scale, QImage.Format.Format_RGBA8888)
    image.fill(0)

    fill_color = QColor(255, 255, 255, 230) if fill is None else QColor(fill)
    outline_color = QColor(0, 0, 0, 200) if outline is None else QColor(outline)

    for y in range(CROSSHAIR_GRID_SIZE):
        for x in range(CROSSHAIR_GRID_SIZE):
            if pixels[y][x] != "1":
                continue
            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    nx = int(x) + int(ox)
                    ny = int(y) + int(oy)
                    if int(nx) < 0 or int(ny) < 0 or int(nx) >= int(CROSSHAIR_GRID_SIZE) or int(ny) >= int(CROSSHAIR_GRID_SIZE):
                        continue
                    if pixels[ny][nx] == "1":
                        continue
                    _fill_scaled_pixel(image, nx, ny, pixel_scale, outline_color)

    for y in range(CROSSHAIR_GRID_SIZE):
        for x in range(CROSSHAIR_GRID_SIZE):
            if pixels[y][x] == "1":
                _fill_scaled_pixel(image, x, y, pixel_scale, fill_color)

    return image

def _fill_scaled_pixel(image: QImage, x: int, y: int, scale: int, color: QColor) -> None:
    base_x = int(x) * int(scale)
    base_y = int(y) * int(scale)
    rgba = color.rgba()
    for py in range(int(scale)):
        for px in range(int(scale)):
            image.setPixel(base_x + px, base_y + py, rgba)