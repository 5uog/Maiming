# FILE: src/maiming/presentation/widgets/hud/hud_widget.py
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QLabel

from maiming.presentation.hud.hud_payload import HudPayload

@dataclass(frozen=True)
class _FitResult:
    text: str
    w: int
    h: int

class HUDWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._margin = 10
        self._pad_px = 8
        self._border_px = 1

        self._max_panel_w = 460

        self._lbl = QLabel(self)
        self._lbl.setObjectName("hud")
        self._lbl.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._lbl.setTextFormat(Qt.TextFormat.PlainText)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._lbl.setWordWrap(True)
        self._lbl.setText("")

        f = QFont(self._lbl.font())
        if int(f.pointSize()) <= 0:
            f.setPointSize(12)
        self._lbl.setFont(f)

        self._raw_text = ""

    def set_payload(self, payload: HudPayload) -> None:
        t = ""
        if isinstance(payload, HudPayload):
            t = str(payload.text or "")
        if t == self._raw_text:
            return
        self._raw_text = t
        self._lbl.setText(self._raw_text)
        self._relayout()

    def resizeEvent(self, _e) -> None:
        self._relayout()

    def _inner_text_width(self, label_w: int) -> int:
        pad = int(self._pad_px)
        bor = int(self._border_px)
        return max(1, int(label_w) - 2 * (pad + bor))

    def _height_for(self, text: str, font: QFont, label_w: int) -> int:
        raw = str(text or "")
        if not raw.strip():
            return int(2 * (self._pad_px + self._border_px) + 2)

        inner_w = self._inner_text_width(int(label_w))
        fm = QFontMetrics(font)
        r = fm.boundingRect(QRect(0, 0, int(inner_w), 100000), int(Qt.TextFlag.TextWordWrap), raw)

        pad_total = 2 * (int(self._pad_px) + int(self._border_px))
        return int(max(1, int(r.height()) + pad_total + 2))

    def _trim_to_height(self, text: str, font: QFont, label_w: int, max_label_h: int) -> tuple[str, int]:
        raw = str(text or "")
        if not raw.strip():
            h = int(2 * (self._pad_px + self._border_px) + 2)
            return "", int(min(max_label_h, h))

        inner_w = self._inner_text_width(int(label_w))
        fm = QFontMetrics(font)

        pad_total = 2 * (int(self._pad_px) + int(self._border_px))
        max_text_h = int(max(1, int(max_label_h) - pad_total - 2))

        kept = raw.splitlines()
        if not kept:
            h = self._height_for(raw, font, label_w)
            return raw, int(min(max_label_h, h))

        while kept:
            cand = "\n".join(kept).strip()
            r = fm.boundingRect(QRect(0, 0, int(inner_w), 100000), int(Qt.TextFlag.TextWordWrap), cand)
            if int(r.height()) <= int(max_text_h):
                h = int(r.height()) + int(pad_total) + 2
                return cand, int(max(1, min(int(max_label_h), h)))
            kept.pop()

        h = int(pad_total) + 2
        return "", int(max(1, min(int(max_label_h), h)))

    def _relayout(self) -> None:
        w = int(self.width())
        h = int(self.height())
        if w <= 1 or h <= 1:
            return

        m = int(self._margin)
        aw = max(1, w - 2 * m)
        ah = max(1, h - 2 * m)

        panel_w = int(max(260, min(int(self._max_panel_w), int(aw))))

        font = QFont(self._lbl.font())
        text = str(self._raw_text or "")

        need_h = self._height_for(text, font, panel_w)
        if int(need_h) > int(ah):
            text, need_h = self._trim_to_height(text, font, panel_w, ah)

        self._lbl.setText(text)
        self._lbl.setFixedWidth(int(panel_w))
        self._lbl.setFixedHeight(int(max(1, min(int(need_h), int(ah)))))

        self._lbl.move(int(m), int(m))
        self._lbl.raise_()