# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QImage

PLAYER_SKIN_KIND_ALEX = "alex"
PLAYER_SKIN_KIND_CUSTOM = "custom"

_SKIN_WIDTH = 64
_SKIN_HEIGHT = 64

def normalize_player_skin_kind(value: object) -> str:
    text = str(value or "").strip().lower()
    if text == PLAYER_SKIN_KIND_CUSTOM:
        return PLAYER_SKIN_KIND_CUSTOM
    return PLAYER_SKIN_KIND_ALEX

def default_player_skin_path(project_root: Path) -> Path:
    return Path(project_root) / "assets" / "minecraft" / "skins" / "alex.png"

def custom_player_skin_path(project_root: Path) -> Path:
    return Path(project_root) / "configs" / "player_skin.png"

def normalize_player_skin_image(image: QImage) -> QImage:
    candidate = QImage(image)
    if candidate.isNull():
        raise ValueError("The selected skin image could not be decoded.")
    if int(candidate.width()) != int(_SKIN_WIDTH) or int(candidate.height()) != int(_SKIN_HEIGHT):
        raise ValueError("Only modern 64x64 Minecraft skin textures are accepted.")
    return candidate.convertToFormat(QImage.Format.Format_RGBA8888)

def load_player_skin_image(project_root: Path, *, kind: object) -> QImage:
    normalized_kind = normalize_player_skin_kind(kind)
    if normalized_kind == PLAYER_SKIN_KIND_CUSTOM:
        custom_path = custom_player_skin_path(project_root)
        custom_image = QImage(str(custom_path))
        if not custom_image.isNull():
            try:
                return normalize_player_skin_image(custom_image)
            except ValueError:
                pass
    default_image = QImage(str(default_player_skin_path(project_root)))
    if default_image.isNull():
        raise RuntimeError("The bundled Alex skin texture could not be loaded.")
    return normalize_player_skin_image(default_image)

def write_custom_player_skin(project_root: Path, image: QImage) -> None:
    normalized = normalize_player_skin_image(image)
    target = custom_player_skin_path(project_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not normalized.save(str(target), "PNG"):
        raise RuntimeError(f"Unable to save the custom player skin to {target}.")

def delete_custom_player_skin(project_root: Path) -> None:
    target = custom_player_skin_path(project_root)
    if target.exists():
        target.unlink()