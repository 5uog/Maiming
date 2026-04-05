# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .sidebar_dialog import SidebarDialogBase


class ThemedNoticeDialog(SidebarDialogBase):

    def __init__(self, *, parent=None, title: str, message: str, nav_label: str="Notice", confirm_text: str="OK") -> None:
        super().__init__(parent, as_window=True, root_object_name="settingsRoot", window_title=str(title), window_size=(760, 520), minimum_window_size=(640, 420), panel_minimum_size=(580, 320), sidebar_object_name="settingsSidebar", content_object_name="settingsContent", stack_object_name="settingsStack")
        self._tab_notice = self._make_tab_button(str(nav_label), 0, self._set_page)
        self._sidebar_layout.addWidget(self._tab_notice)
        self._sidebar_layout.addStretch(1)

        scroll, host, layout = self._make_scroll_page()

        title_label = QLabel(str(title), host)
        title_label.setObjectName("sectionTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        body_label = QLabel(str(message), host)
        body_label.setObjectName("subtitle")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)
        layout.addStretch(1)
        self._stack.addWidget(scroll)

        footer = QWidget(self)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 14, 18, 0)
        footer_layout.setSpacing(12)
        footer_layout.addStretch(1)
        self._confirm_button = QPushButton(str(confirm_text), footer)
        self._confirm_button.setObjectName("menuBtn")
        self._confirm_button.clicked.connect(self.accept)
        footer_layout.addWidget(self._confirm_button)
        self._content_layout.addWidget(footer)
        self._set_page(0)

    def _set_page(self, index: int) -> None:
        self._set_stack_page(index=index, max_index=0, tab_buttons=(self._tab_notice,))


def _resolve_viewport_host(root) -> object | None:
    queue = [root]
    visited: set[int] = set()
    while queue:
        current = queue.pop(0)
        if current is None:
            continue
        current_id = int(id(current))
        if current_id in visited:
            continue
        visited.add(current_id)
        if hasattr(current, "_begin_transient_modal") and hasattr(current, "_end_transient_modal"):
            return current
        candidates = []
        viewport = getattr(current, "viewport", None)
        if viewport is not None:
            candidates.append(viewport)
        owned_viewport = getattr(current, "_viewport", None)
        if owned_viewport is not None:
            candidates.append(owned_viewport)
        screen = getattr(current, "_screen", None)
        if screen is not None:
            screen_viewport = getattr(screen, "viewport", None)
            if screen_viewport is not None:
                candidates.append(screen_viewport)
        if hasattr(current, "parentWidget") and callable(getattr(current, "parentWidget")):
            try:
                candidates.append(current.parentWidget())
            except Exception:
                pass
        if hasattr(current, "parent") and callable(getattr(current, "parent")):
            try:
                candidates.append(current.parent())
            except Exception:
                pass
        if hasattr(current, "window") and callable(getattr(current, "window")):
            try:
                host_window = current.window()
                if host_window is not current:
                    candidates.append(host_window)
            except Exception:
                pass
        queue.extend(candidate for candidate in candidates if candidate is not None)
    return None


def show_themed_notice(*, parent=None, title: str, message: str, nav_label: str="Notice", confirm_text: str="OK") -> None:
    dialog = ThemedNoticeDialog(parent=parent, title=str(title), message=str(message), nav_label=str(nav_label), confirm_text=str(confirm_text))
    if parent is not None and hasattr(parent, "_position_detached_overlay_window"):
        try:
            parent._position_detached_overlay_window(dialog)
        except Exception:
            pass
    elif hasattr(parent, "window") and callable(getattr(parent, "window")):
        try:
            host_window = parent.window()
            if host_window is not None and hasattr(host_window, "_position_detached_overlay_window"):
                host_window._position_detached_overlay_window(dialog)
        except Exception:
            pass
    viewport = _resolve_viewport_host(parent)
    if viewport is not None:
        try:
            viewport._begin_transient_modal()
        except Exception:
            viewport = None
    try:
        dialog.exec()
    finally:
        if viewport is not None:
            try:
                viewport._end_transient_modal()
            except Exception:
                pass
