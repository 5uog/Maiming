# FILE: src/maiming/presentation/widgets/hud/hud_widget.py
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QLabel

@dataclass(frozen=True)
class _FitResult:
    text: str
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
        self._panel_gap = 12
        self._max_panel_w = 460

        self._lbl_left = self._make_label()
        self._lbl_right = self._make_label()

        self._raw_left_text = ""
        self._raw_right_text = ""

    def _make_label(self) -> QLabel:
        lbl = QLabel(self)
        lbl.setObjectName("hud")
        lbl.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lbl.setTextFormat(Qt.TextFormat.PlainText)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        lbl.setWordWrap(True)
        lbl.setText("")

        f = QFont(lbl.font())
        if int(f.pointSize()) <= 0:
            f.setPointSize(12)
        lbl.setFont(f)
        return lbl

    @staticmethod
    def _coerce_texts(payload: object) -> tuple[str, str]:
        if payload is None:
            return "", ""

        if isinstance(payload, str):
            return str(payload), ""

        left = getattr(payload, "left_text", None)
        right = getattr(payload, "right_text", None)

        if left is not None:
            return str(left), str(right or "")

        text = getattr(payload, "text", None)
        return (str(text), "") if text is not None else ("", "")

    def set_payload(self, payload: object) -> None:
        left, right = self._coerce_texts(payload)
        if left == self._raw_left_text and right == self._raw_right_text:
            return

        self._raw_left_text = left
        self._raw_right_text = right
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

    def _trim_to_height(self, text: str, font: QFont, label_w: int, max_label_h: int) -> _FitResult:
        raw = str(text or "")
        if not raw.strip():
            h = int(2 * (self._pad_px + self._border_px) + 2)
            return _FitResult(text="", h=int(min(max_label_h, h)))

        inner_w = self._inner_text_width(int(label_w))
        fm = QFontMetrics(font)

        pad_total = 2 * (int(self._pad_px) + int(self._border_px))
        max_text_h = int(max(1, int(max_label_h) - pad_total - 2))

        kept = raw.splitlines()
        while kept:
            cand = "\n".join(kept).strip()
            r = fm.boundingRect(QRect(0, 0, int(inner_w), 100000), int(Qt.TextFlag.TextWordWrap), cand)
            if int(r.height()) <= int(max_text_h):
                h = int(r.height()) + int(pad_total) + 2
                return _FitResult(text=cand, h=int(max(1, min(int(max_label_h), h))))
            kept.pop()

        h = int(pad_total) + 2
        return _FitResult(text="", h=int(max(1, min(int(max_label_h), h))))

    def _fit_text(self, text: str, label: QLabel, label_w: int, max_label_h: int) -> _FitResult:
        font = QFont(label.font())
        need_h = self._height_for(str(text or ""), font, int(label_w))
        if int(need_h) <= int(max_label_h):
            return _FitResult(text=str(text or ""), h=int(need_h))
        return self._trim_to_height(str(text or ""), font, int(label_w), int(max_label_h))

    def _apply_label(self, *, label: QLabel, text: str, x: int, y: int, w: int, h_max: int) -> None:
        raw = str(text or "")
        if not raw.strip():
            label.setVisible(False)
            return

        fit = self._fit_text(raw, label, int(w), int(h_max))
        label.setText(str(fit.text))
        label.setFixedWidth(int(max(1, int(w))))
        label.setFixedHeight(int(max(1, int(fit.h))))
        label.move(int(x), int(y))
        label.setVisible(True)
        label.raise_()

    def _relayout(self) -> None:
        w = int(self.width())
        h = int(self.height())
        if w <= 1 or h <= 1:
            return

        m = int(self._margin)
        aw = max(1, w - 2 * m)
        ah = max(1, h - 2 * m)

        left_on = bool(str(self._raw_left_text).strip())
        right_on = bool(str(self._raw_right_text).strip())

        if left_on and right_on:
            panel_w = max(1, min(int(self._max_panel_w), (int(aw) - int(self._panel_gap)) // 2))
        else:
            panel_w = max(1, min(int(self._max_panel_w), int(aw)))

        self._apply_label(
            label=self._lbl_left,
            text=self._raw_left_text,
            x=int(m),
            y=int(m),
            w=int(panel_w),
            h_max=int(ah),
        )

        self._apply_label(
            label=self._lbl_right,
            text=self._raw_right_text,
            x=int(w - m - panel_w),
            y=int(m),
            w=int(panel_w),
            h_max=int(ah),
        )