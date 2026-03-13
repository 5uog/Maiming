# FILE: src/maiming/presentation/hud/hud_payload.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class HudPayload:
    left_text: str
    right_text: str = ""

    @property
    def text(self) -> str:
        return str(self.left_text)