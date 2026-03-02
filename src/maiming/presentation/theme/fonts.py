# FILE: src/maiming/presentation/theme/fonts.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

@dataclass(frozen=True)
class FontInstallResult:
    ok: bool
    family: str

def install_minecraft_fonts(*, font_dir: Path) -> FontInstallResult:
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
    fam = str(family)
    if not fam:
        return
    app.setFont(QFont(fam, int(max(1, point_size))))