# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QLabel, QWidget

from ....shared.ui.hud.hud_payload import HudPayload
from ....shared.ui.hud.hud_widget import HUDWidget


class OthelloEvaluationGraphWidget(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("othelloGraph")
        self._samples: tuple[tuple[int, float, bool], ...] = ()
        self._current_edge: float | None = None

    def set_samples(self, *, samples: tuple[tuple[int, float, bool], ...], current_edge: float | None) -> None:
        self._samples = tuple((int(depth), float(score), bool(solved)) for depth, score, solved in tuple(samples))
        self._current_edge = None if current_edge is None else float(current_edge)
        self.setVisible(bool(self._samples))
        self.update()

    def paintEvent(self, _event) -> None:
        if not self._samples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(16, 16, 16, 172))

        width = max(1, int(self.width()))
        height = max(1, int(self.height()))
        margin_x = 12
        margin_y = 12
        chart_left = float(margin_x)
        chart_top = float(margin_y)
        chart_width = max(1.0, float(width - margin_x * 2))
        chart_height = max(1.0, float(height - margin_y * 2))
        center_y = float(chart_top) + float(chart_height) * 0.5

        max_abs = max(abs(float(score)) for _depth, score, _solved in self._samples)
        if self._current_edge is not None:
            max_abs = max(float(max_abs), abs(float(self._current_edge)))
        max_abs = max(1.0, float(max_abs))

        painter.setPen(QPen(QColor(255, 255, 255, 42), 1.0))
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = float(chart_top) + float(chart_height) * float(fraction)
            painter.drawLine(int(chart_left), int(round(y)), int(round(chart_left + chart_width)), int(round(y)))

        zero_pen = QPen(QColor(255, 255, 255, 96), 1.5)
        painter.setPen(zero_pen)
        painter.drawLine(int(chart_left), int(round(center_y)), int(round(chart_left + chart_width)), int(round(center_y)))

        if len(self._samples) == 1:
            points = [(float(chart_left) + float(chart_width) * 0.5, float(center_y) - (float(self._samples[0][1]) / float(max_abs)) * float(chart_height) * 0.42, bool(self._samples[0][2]))]
        else:
            points = []
            count = len(self._samples) - 1
            for index, (_depth, score, solved) in enumerate(self._samples):
                x = float(chart_left) + (float(index) / float(count)) * float(chart_width)
                y = float(center_y) - (float(score) / float(max_abs)) * float(chart_height) * 0.42
                points.append((float(x), float(y), bool(solved)))

        path = QPainterPath()
        first_x, first_y, _first_solved = points[0]
        path.moveTo(float(first_x), float(first_y))
        for x, y, _solved in points[1:]:
            path.lineTo(float(x), float(y))

        line_color = QColor(118, 214, 103, 255) if (self._current_edge is None or float(self._current_edge) >= 0.0) else QColor(255, 160, 96, 255)
        painter.setPen(QPen(line_color, 2.25))
        painter.drawPath(path)

        for x, y, solved in points:
            point_color = QColor(255, 222, 95, 255) if bool(solved) else line_color
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(point_color)
            painter.drawEllipse(int(round(float(x) - 2.5)), int(round(float(y) - 2.5)), 5, 5)


class OthelloHudWidget(HUDWidget):

    def __init__(self, parent=None) -> None:
        super().__init__()
        if parent is not None:
            self.setParent(parent)

        self._title_label = QLabel(self)
        self._title_label.setObjectName("othelloTitle")
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setText("")
        self._graph_widget = OthelloEvaluationGraphWidget(self)
        self._graph_widget.setVisible(False)

        self._title_text = ""
        self._graph_samples: tuple[tuple[int, float, bool], ...] = ()
        self._graph_current_edge: float | None = None

    def set_texts(self, *, left_text: str, right_text: str="", title_text: str="", graph_samples: tuple[tuple[int, float, bool], ...] = (), graph_current_edge: float | None = None) -> None:
        next_title = str(title_text)
        title_changed = bool(next_title != self._title_text)
        self._title_text = next_title
        self._graph_samples = tuple((int(depth), float(score), bool(solved)) for depth, score, solved in tuple(graph_samples))
        self._graph_current_edge = None if graph_current_edge is None else float(graph_current_edge)
        self._graph_widget.set_samples(samples=self._graph_samples, current_edge=self._graph_current_edge)
        self.set_payload(HudPayload(left_text=str(left_text), right_text=str(right_text)))
        if bool(title_changed):
            self._relayout_title()
        self._relayout_graph()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout_title()
        self._relayout_graph()

    def _relayout(self) -> None:
        super()._relayout()
        self._relayout_title()
        self._relayout_graph()

    def _relayout_title(self) -> None:
        title_text = str(self._title_text).strip()
        self._title_label.setText(title_text)
        if not title_text or int(self.width()) <= 1 or int(self.height()) <= 1:
            self._title_label.setVisible(False)
            return

        width = min(max(360, self.width() - 96), 980)
        height = max(64, self._title_label.sizeHint().height() + 18)
        x = max(0,(self.width() - int(width)) // 2)
        y = max(18, min(max(18, self.height() // 6), max(18, self.height() - int(height) - 18)))
        self._title_label.setGeometry(int(x), int(y), int(width), int(height))
        self._title_label.setVisible(True)
        self._title_label.raise_()

    def _relayout_graph(self) -> None:
        if not self._graph_samples or int(self.width()) <= 1 or int(self.height()) <= 1:
            self._graph_widget.setVisible(False)
            return

        label = self._lbl_right
        panel_w = min(460, max(300, self.width() // 3))
        x = max(10, int(self.width()) - panel_w - 10)
        if label.isVisible():
            x = int(label.geometry().x())
            panel_w = int(label.geometry().width())
            top_y = int(label.geometry().bottom()) + 12
        else:
            top_y = 10

        height = min(180, max(120, self.height() // 4))
        max_height = max(0, int(self.height()) - top_y - 10)
        if int(max_height) < 72:
            self._graph_widget.setVisible(False)
            return

        self._graph_widget.setGeometry(int(x), int(top_y), int(panel_w), int(min(int(height), int(max_height))))
        self._graph_widget.setVisible(True)
        self._graph_widget.raise_()
