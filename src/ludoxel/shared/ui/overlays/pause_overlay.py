# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QImage, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ...world.play_space import PLAY_SPACE_MY_WORLD, is_othello_space, is_my_world_space, normalize_play_space_id
from .player_skin_preview_widget import PlayerSkinPreviewWidget


class PauseOverlay(QWidget):
    resume_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    play_my_world_requested = pyqtSignal()
    play_othello_requested = pyqtSignal()
    save_quit_requested = pyqtSignal()
    change_skin_requested = pyqtSignal()
    reset_skin_requested = pyqtSignal()
    preview_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)

        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("pauseRoot")
        self.setMouseTracking(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(56, 44, 56, 44)
        root.setSpacing(40)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(0)
        left_column.addStretch(1)

        left_content = QWidget(self)
        left_content_layout = QVBoxLayout(left_content)
        left_content_layout.setContentsMargins(0, 0, 0, 0)
        left_content_layout.setSpacing(18)

        self._title_mark = QLabel(left_content)
        self._title_mark.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._title_mark.setVisible(False)
        left_content_layout.addWidget(self._title_mark, alignment=Qt.AlignmentFlag.AlignHCenter)

        panel = QFrame(self)
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        panel.setMinimumWidth(420)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 20)
        panel_layout.setSpacing(12)

        btn_resume = QPushButton("Resume", panel)
        btn_resume.setObjectName("menuBtn")
        btn_resume.clicked.connect(self.resume_requested.emit)
        panel_layout.addWidget(btn_resume)

        btn_settings = QPushButton("Settings", panel)
        btn_settings.setObjectName("menuBtn")
        btn_settings.clicked.connect(self.settings_requested.emit)
        panel_layout.addWidget(btn_settings)

        self._btn_my_world = QPushButton("Play My World", panel)
        self._btn_my_world.setObjectName("menuBtn")
        self._btn_my_world.clicked.connect(self.play_my_world_requested.emit)
        panel_layout.addWidget(self._btn_my_world)

        self._btn_othello = QPushButton("Play Othello (Reversi)", panel)
        self._btn_othello.setObjectName("menuBtn")
        self._btn_othello.clicked.connect(self.play_othello_requested.emit)
        panel_layout.addWidget(self._btn_othello)

        btn_save_quit = QPushButton("Save && Quit", panel)
        btn_save_quit.setObjectName("menuBtn")
        btn_save_quit.clicked.connect(self.save_quit_requested.emit)
        panel_layout.addWidget(btn_save_quit)

        left_content_layout.addWidget(panel, alignment=Qt.AlignmentFlag.AlignCenter)
        left_column.addWidget(left_content, alignment=Qt.AlignmentFlag.AlignCenter)
        left_column.addStretch(1)

        self._right_column = QVBoxLayout()
        self._right_column.setContentsMargins(0, 0, 0, 0)
        self._right_column.setSpacing(0)
        self._right_column.addStretch(1)

        right_content = QWidget(self)
        self._right_content_layout = QVBoxLayout(right_content)
        self._right_content_layout.setContentsMargins(0, 0, 0, 0)
        self._right_content_layout.setSpacing(4)

        self._skin_preview = PlayerSkinPreviewWidget(self)
        self._skin_preview.view_changed.connect(self.preview_changed.emit)
        self._right_content_layout.addWidget(self._skin_preview, stretch=0, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._skin_actions = QWidget(self)
        actions = QVBoxLayout(self._skin_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)

        btn_change_skin = QPushButton("Change Skin", self)
        btn_change_skin.setObjectName("menuBtn")
        btn_change_skin.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_change_skin.setMinimumWidth(240)
        btn_change_skin.clicked.connect(self.change_skin_requested.emit)
        actions.addWidget(btn_change_skin, alignment=Qt.AlignmentFlag.AlignHCenter)

        btn_reset_skin = QPushButton("Reset to Alex", self)
        btn_reset_skin.setObjectName("menuBtn")
        btn_reset_skin.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_reset_skin.setMinimumWidth(240)
        btn_reset_skin.clicked.connect(self.reset_skin_requested.emit)
        actions.addWidget(btn_reset_skin, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._right_content_layout.addWidget(self._skin_actions, stretch=0, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._right_column.addWidget(right_content, stretch=0, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._right_column.addStretch(1)

        root.addLayout(left_column, stretch=1)
        root.addLayout(self._right_column, stretch=1)

        self._install_pointer_tracking()
        self.set_current_space(PLAY_SPACE_MY_WORLD)

    def set_current_space(self, space_id: str) -> None:
        normalized = normalize_play_space_id(space_id)
        self._btn_my_world.setEnabled(not is_my_world_space(normalized))
        self._btn_othello.setEnabled(not is_othello_space(normalized))

    def set_player_skin(self, image: QImage, *, slim_arm: bool) -> None:
        self._skin_preview.set_skin(image, slim_arm=bool(slim_arm))

    def set_player_preview_frame(self, image: QImage) -> None:
        self._skin_preview.set_frame_image(image)

    def set_player_preview_name_tag(self, text: str, *, visible: bool, opacity: float = 1.0) -> None:
        self._skin_preview.set_name_tag(text, visible=bool(visible), opacity=float(opacity))

    def player_preview_angles(self) -> tuple[float, float, float]:
        return self._skin_preview.preview_angles()

    def player_preview_size(self) -> tuple[int, int]:
        return (int(self._skin_preview.width()), int(self._skin_preview.height()))

    def eventFilter(self, watched, event) -> bool:
        event_type = event.type()
        if event_type == QEvent.Type.MouseButtonPress and hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
            pos = self._map_event_position(watched, event)
            if pos is not None:
                self._skin_preview.begin_drag(x=float(pos.x()))
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.preview_changed.emit()
        elif event_type == QEvent.Type.MouseMove and hasattr(event, "position"):
            pos = self._map_event_position(watched, event)
            if pos is not None:
                self._skin_preview.move_pointer(x=float(pos.x()), y=float(pos.y()), area_width=int(self.width()), area_height=int(self.height()))
                self.preview_changed.emit()
        elif event_type == QEvent.Type.MouseButtonRelease and hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
            pos = self._map_event_position(watched, event)
            if pos is not None:
                self._skin_preview.end_drag(x=float(pos.x()), y=float(pos.y()), area_width=int(self.width()), area_height=int(self.height()))
            else:
                self._skin_preview.note_pointer_left()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.preview_changed.emit()
        elif event_type == QEvent.Type.Enter and watched is self:
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(cursor_pos):
                self._skin_preview.note_pointer_entered(x=float(cursor_pos.x()), y=float(cursor_pos.y()), area_width=int(self.width()), area_height=int(self.height()))
                self.preview_changed.emit()
        elif event_type == QEvent.Type.Leave and watched is self:
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            if not self.rect().contains(cursor_pos):
                self._skin_preview.note_pointer_left()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.preview_changed.emit()
        return super().eventFilter(watched, event)

    def keyPressEvent(self, e) -> None:
        if int(e.key()) == int(Qt.Key.Key_Escape):
            self.resume_requested.emit()
            return
        super().keyPressEvent(e)

    def _install_pointer_tracking(self) -> None:
        for widget in (self, *self.findChildren(QWidget)):
            widget.installEventFilter(self)
            widget.setMouseTracking(True)

    def _map_event_position(self, watched, event):
        if not isinstance(watched, QWidget) or not hasattr(event, "position"):
            return None
        return watched.mapTo(self, event.position().toPoint())

    def set_title_image_path(self, path: Path | None) -> None:
        pixmap = QPixmap()
        if path is not None:
            pixmap = QPixmap(str(Path(path).resolve()))
        if pixmap.isNull():
            self._title_mark.clear()
            self._title_mark.setVisible(False)
            return
        scaled = pixmap.scaled(420, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._title_mark.setPixmap(scaled)
        self._title_mark.setVisible(True)
