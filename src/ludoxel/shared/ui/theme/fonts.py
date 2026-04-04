# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication


@dataclass(frozen=True)
class FontInstallResult:
    ok: bool
    family: str
    fallback_families: tuple[str, ...] = ()


def install_minecraft_fonts(*, font_dir: Path) -> FontInstallResult:
    d = Path(font_dir)

    primary_candidates = (d / "MinecraftBold-nMK1.otf", d / "MinecraftBoldItalic-1y1e.otf", d / "MinecraftItalic-R8Mo.otf", d / "MinecraftRegular-Bmg3.otf")
    fallback_candidates = (d / "KaiseiOpti-Regular.ttf", d / "KaiseiOpti-Medium.ttf", d / "KaiseiOpti-Bold.ttf")

    primary_families: list[str] = []
    fallback_families: list[str] = []
    for p in primary_candidates:
        if not p.exists():
            continue

        fid = int(QFontDatabase.addApplicationFont(str(p)))
        if fid < 0:
            continue

        for fam in QFontDatabase.applicationFontFamilies(fid):
            s = str(fam)
            if s and (s not in primary_families):
                primary_families.append(s)

    for p in fallback_candidates:
        if not p.exists():
            continue

        fid = int(QFontDatabase.addApplicationFont(str(p)))
        if fid < 0:
            continue

        for fam in QFontDatabase.applicationFontFamilies(fid):
            s = str(fam)
            if s and (s not in fallback_families):
                fallback_families.append(s)

    if not primary_families:
        return FontInstallResult(ok=False, family="")

    preferred = ""
    for fam in primary_families:
        if "Minecraft" in fam:
            preferred = fam
            break
    if not preferred:
        preferred = primary_families[0]

    ordered_fallback_families = tuple(str(fam) for fam in fallback_families if str(fam) and str(fam) != str(preferred))
    return FontInstallResult(ok=True, family=str(preferred), fallback_families=ordered_fallback_families)


def apply_application_font(*, app: QApplication, family: str, point_size: int=12, fallback_families: tuple[str, ...]=()) -> None:
    fam = str(family)
    if not fam:
        return
    font = QFont()
    font.setPointSize(int(max(1, point_size)))
    families = [fam, *(str(candidate) for candidate in tuple(fallback_families) if str(candidate).strip())]
    if hasattr(font, "setFamilies"):
        font.setFamilies(families)
    else:
        font.setFamily(fam)
    app.setFont(font)
