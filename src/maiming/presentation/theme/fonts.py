# FILE: src/maiming/presentation/theme/fonts.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

@dataclass(frozen=True)
class FontInstallResult:
    """
    The returned family name is resolved from the font's internal metadata rather than the filename.
    This matters because Qt's style system and QFont selection depend on the family token that the
    font advertises, which cannot be assumed to match a file naming convention.
    """
    ok: bool
    family: str

def install_minecraft_fonts(*, font_dir: Path) -> FontInstallResult:
    """
    This installer registers the bundled Minecraft font faces into the Qt application font database
    and selects a stable family name for application-wide use. The selection prefers a family token
    containing 'Minecraft' when available, while remaining functional when the font metadata uses a
    different family label on a given platform.
    """
    d = Path(font_dir)

    candidates = (
        d / "MinecraftBold-nMK1.otf",
        d / "MinecraftBoldItalic-1y1e.otf",
        d / "MinecraftItalic-R8Mo.otf",
        d / "MinecraftRegular-Bmg3.otf",
    )

    families: list[str] = []
    for p in candidates:
        if not p.exists():
            continue

        fid = int(QFontDatabase.addApplicationFont(str(p)))
        if fid < 0:
            continue

        for fam in QFontDatabase.applicationFontFamilies(fid):
            s = str(fam)
            if s and (s not in families):
                families.append(s)

    if not families:
        return FontInstallResult(ok=False, family="")

    preferred = ""
    for fam in families:
        if "Minecraft" in fam:
            preferred = fam
            break
    if not preferred:
        preferred = families[0]

    return FontInstallResult(ok=True, family=str(preferred))

def apply_application_font(*, app: QApplication, family: str, point_size: int = 12) -> None:
    """
    The QApplication default font is set explicitly so that widgets and style sheets that do not
    hardcode a font-family still render with the bundled typeface.
    """
    fam = str(family)
    if not fam:
        return
    app.setFont(QFont(fam, int(max(1, point_size))))