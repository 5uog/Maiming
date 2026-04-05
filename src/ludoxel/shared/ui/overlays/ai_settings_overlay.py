# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ....application.runtime.ai_player_types import AI_MODE_IDLE, AI_MODE_ROUTE, AI_MODE_WANDER, AI_PERSONALITY_AGGRESSIVE, AI_PERSONALITY_PEACEFUL, AI_ROUTE_STYLE_FLEXIBLE, AI_ROUTE_STYLE_STRICT, AiSpawnEggSettings
from ..common.sidebar_dialog import SidebarDialogBase
from ..common.themed_notice_dialog import show_themed_notice


class AiSettingsOverlay(SidebarDialogBase):

    def __init__(self, *, parent: QWidget | None=None, settings: AiSpawnEggSettings) -> None:
        super().__init__(parent, as_window=True, root_object_name="settingsRoot", window_title="AI Settings", window_size=(920, 720), minimum_window_size=(820, 640), panel_minimum_size=(760, 560), sidebar_object_name="settingsSidebar", content_object_name="settingsContent", stack_object_name="settingsStack")
        self._settings = settings.normalized()
        self._edit_route_requested = False
        self._delete_requested = False

        self._tab_behavior = self._make_tab_button("Behavior", 0, self._set_page)
        self._tab_route = self._make_tab_button("Route", 1, self._set_page)
        self._sidebar_layout.addWidget(self._tab_behavior)
        self._sidebar_layout.addWidget(self._tab_route)
        self._sidebar_layout.addStretch(1)
        self._delete_button = self._make_tab_button("Delete AI", 99, self._request_delete)
        self._delete_button.setChecked(False)
        self._delete_button.setAutoExclusive(False)
        self._sidebar_layout.addWidget(self._delete_button)

        self._build_behavior_page()
        self._build_route_page()
        self._build_footer()
        self._load_settings(self._settings)
        self._sync_route_controls()
        self._set_page(0)

    def _build_behavior_page(self) -> None:
        scroll, host, layout = self._make_scroll_page()

        title = QLabel("AI behavior", host)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("This overlay edits the selected AI instance. Newly spawned AI stays on standby until a role is assigned here.", host)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        mode_label = QLabel("Mode", host)
        mode_label.setObjectName("valueLabel")
        layout.addWidget(mode_label)
        self._mode_combo = QComboBox(host)
        self._mode_combo.addItem("Standby", userData=AI_MODE_IDLE)
        self._mode_combo.addItem("Free Roam / PVP", userData=AI_MODE_WANDER)
        self._mode_combo.addItem("Route Patrol", userData=AI_MODE_ROUTE)
        layout.addWidget(self._mode_combo)

        personality_label = QLabel("Personality", host)
        personality_label.setObjectName("valueLabel")
        layout.addWidget(personality_label)
        self._personality_combo = QComboBox(host)
        self._personality_combo.addItem("Aggressive", userData=AI_PERSONALITY_AGGRESSIVE)
        self._personality_combo.addItem("Peaceful", userData=AI_PERSONALITY_PEACEFUL)
        layout.addWidget(self._personality_combo)

        self._can_place_blocks = QCheckBox("Allow block placement", host)
        layout.addWidget(self._can_place_blocks)

        self._mode_description = QLabel("", host)
        self._mode_description.setObjectName("subtitle")
        self._mode_description.setWordWrap(True)
        layout.addWidget(self._mode_description)
        layout.addStretch(1)
        self._stack.addWidget(scroll)

    def _build_route_page(self) -> None:
        scroll, host, layout = self._make_scroll_page()

        title = QLabel("Route controls", host)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Route patrol uses the dedicated route hotbar. The first slot confirms the draft, the second slot is the eraser, and the rightmost slot cancels the edit.", host)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        route_style_label = QLabel("Route style", host)
        route_style_label.setObjectName("valueLabel")
        layout.addWidget(route_style_label)
        self._route_style_combo = QComboBox(host)
        self._route_style_combo.addItem("Strict", userData=AI_ROUTE_STYLE_STRICT)
        self._route_style_combo.addItem("Flexible", userData=AI_ROUTE_STYLE_FLEXIBLE)
        layout.addWidget(self._route_style_combo)

        self._route_run = QCheckBox("Run route segments", host)
        layout.addWidget(self._route_run)

        self._route_closed = QCheckBox("Treat route as a closed loop", host)
        layout.addWidget(self._route_closed)

        self._route_summary = QLabel("", host)
        self._route_summary.setObjectName("subtitle")
        self._route_summary.setWordWrap(True)
        layout.addWidget(self._route_summary)

        button_row = QHBoxLayout()
        self._edit_route_button = QPushButton("Edit Route", host)
        self._edit_route_button.setObjectName("menuBtn")
        self._edit_route_button.clicked.connect(self._request_route_edit)
        button_row.addWidget(self._edit_route_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addStretch(1)
        self._stack.addWidget(scroll)

    def _build_footer(self) -> None:
        footer = QWidget(self)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 14, 18, 0)
        footer_layout.setSpacing(12)
        footer_layout.addStretch(1)

        self._cancel_button = QPushButton("Cancel", footer)
        self._cancel_button.setObjectName("menuBtn")
        self._cancel_button.clicked.connect(self.reject)
        footer_layout.addWidget(self._cancel_button)

        self._save_button = QPushButton("Save", footer)
        self._save_button.setObjectName("menuBtn")
        self._save_button.clicked.connect(self._accept_with_validation)
        footer_layout.addWidget(self._save_button)
        self._content_layout.addWidget(footer)

    def _set_page(self, index: int) -> None:
        self._set_stack_page(index=index, max_index=1, tab_buttons=(self._tab_behavior, self._tab_route))

    def _load_settings(self, settings: AiSpawnEggSettings) -> None:
        self._settings = settings.normalized()
        self._set_combo_value(self._mode_combo, str(self._settings.mode))
        self._set_combo_value(self._personality_combo, str(self._settings.personality))
        self._set_combo_value(self._route_style_combo, str(self._settings.route_style))
        self._can_place_blocks.setChecked(bool(self._settings.can_place_blocks))
        self._route_run.setChecked(bool(self._settings.route_run))
        self._route_closed.setChecked(bool(self._settings.route_closed))
        self._route_summary.setText(self._route_summary_text())
        self._mode_combo.currentIndexChanged.connect(self._sync_route_controls)
        self._mode_combo.currentIndexChanged.connect(self._sync_mode_description)
        self._sync_mode_description()

    def _route_summary_text(self) -> str:
        point_count = len(self._settings.route_points)
        loop_text = "Closed loop" if bool(self._settings.route_closed) else "Open route"
        return f"{point_count} point(s) recorded. {loop_text}."

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        target = str(value)
        for index in range(combo.count()):
            if str(combo.itemData(index)) == target:
                combo.setCurrentIndex(index)
                return

    def _sync_route_controls(self) -> None:
        route_mode = str(self._mode_combo.currentData()) == AI_MODE_ROUTE
        self._route_style_combo.setEnabled(bool(route_mode))
        self._route_run.setEnabled(bool(route_mode))
        self._route_closed.setEnabled(bool(route_mode))
        self._edit_route_button.setEnabled(True)

    def _sync_mode_description(self) -> None:
        mode = str(self._mode_combo.currentData())
        if mode == AI_MODE_ROUTE:
            self._mode_description.setText("Route Patrol follows the authored path, can engage the player at close range, and returns to the route when the target escapes.")
            return
        if mode == AI_MODE_WANDER:
            self._mode_description.setText("Free Roam / PVP uses the player kinematics, collision, jump, placement, and interaction path and can attack in survival mode when the target is inside the melee line.")
            return
        self._mode_description.setText("Standby keeps the AI waiting at its current position until a role is assigned.")

    def _accept_with_validation(self) -> None:
        if str(self._mode_combo.currentData()) == AI_MODE_ROUTE and len(self._settings.route_points) < 2:
            show_themed_notice(parent=self, title="AI Route", message="Route mode requires at least two route points.", nav_label="AI Route")
            self._set_page(1)
            return
        self.accept()

    def _request_route_edit(self) -> None:
        self._set_combo_value(self._mode_combo, AI_MODE_ROUTE)
        self._sync_route_controls()
        self._sync_mode_description()
        self._edit_route_requested = True
        self.accept()

    def _request_delete(self, _index: int=0) -> None:
        self._delete_requested = True
        self.accept()

    def settings(self) -> AiSpawnEggSettings:
        return AiSpawnEggSettings(mode=str(self._mode_combo.currentData()), personality=str(self._personality_combo.currentData()), can_place_blocks=bool(self._can_place_blocks.isChecked()), route_points=tuple(self._settings.route_points), route_closed=bool(self._route_closed.isChecked()), route_run=bool(self._route_run.isChecked()), route_style=str(self._route_style_combo.currentData())).normalized()

    def route_edit_requested(self) -> bool:
        return bool(self._edit_route_requested)

    def delete_requested(self) -> bool:
        return bool(self._delete_requested)
