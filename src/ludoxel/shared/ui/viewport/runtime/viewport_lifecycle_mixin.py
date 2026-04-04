# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

import time

from PyQt6.QtCore import Qt

from ..controllers import interaction_controller
from ..controllers import settings_controller

if TYPE_CHECKING:
                                                                from ..gl_viewport_widget import GLViewportWidget


class ViewportLifecycleMixin:

    def _on_application_state_changed(self: "GLViewportWidget", state) -> None:
        was_active = bool(self._application_active)
        self._application_active = bool(state == Qt.ApplicationState.ApplicationActive)
        if not bool(self._application_active):
            self._pause_on_application_deactivation = bool(self._inp.captured())
            self._reset_held_mouse_actions()
            self._inp.reset()
            try:
                self._inp.set_mouse_capture(False)
            except Exception:
                pass
            if bool(self._pause_on_application_deactivation) and (not bool(self.loading_active())) and (not self._overlays.dead()):
                self._deactivation_pause_timer.start()
        elif not bool(was_active):
            self._deactivation_pause_timer.stop()
            self._pause_on_application_deactivation = False
            self.arm_resume_refresh()
        else:
            self._deactivation_pause_timer.stop()
            self._pause_on_application_deactivation = False
        settings_controller.sync_cloud_motion_pause(self)
        self._sync_runtime_activity()

    def _pause_after_application_deactivation(self: "GLViewportWidget") -> None:
        if bool(self._application_active):
            return
        if not bool(self._pause_on_application_deactivation):
            return
        if bool(self.loading_active()) or self._overlays.dead():
            return
        interaction_controller.open_pause_menu(self)

    def _sync_runtime_activity(self: "GLViewportWidget") -> None:
        self._set_runtime_active(bool(self._gl_initialized) and bool(self.isVisible()) and bool(self._application_active) and (not bool(self._shutdown_done)))

    def _on_frame_swapped(self: "GLViewportWidget") -> None:
        self._hud_ctl.on_present_frame()

    def _set_runtime_active(self: "GLViewportWidget", active: bool) -> None:
        next_active = bool(active)
        if next_active == bool(self._runtime_active):
            return

        self._runtime_active = bool(next_active)
        if not bool(next_active):
            self._reset_held_mouse_actions()
            try:
                self._sim_timer.stop()
            except Exception:
                pass
            try:
                self._render_timer.stop()
            except Exception:
                pass
            try:
                self._inp.set_mouse_capture(False)
            except Exception:
                pass
            return

        now = time.perf_counter()
        self._runner.start()
        self._last_paint_ms = 0.0
        self._frame_sync.note_runtime_started(now=float(now))
        self.arm_resume_refresh()
        self._sim_timer.start()
        self._render_timer.start()

    def shutdown(self: "GLViewportWidget") -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        self._set_runtime_active(False)
        try:
            self._settings.hide()
        except Exception:
            pass
        try:
            self._othello_settings.hide()
        except Exception:
            pass
        try:
            self._sim_timer.stop()
        except Exception:
            pass
        try:
            self._render_timer.stop()
        except Exception:
            pass
        try:
            self._inp.set_mouse_capture(False)
        except Exception:
            pass
        try:
            self.save_state()
        except Exception:
            pass
        try:
            self._othello_ai.shutdown()
        except Exception:
            pass
        try:
            self._audio.shutdown()
        except Exception:
            pass
        try:
            if self.context() is not None:
                self.makeCurrent()
                try:
                    self._renderer.destroy()
                finally:
                    self.doneCurrent()
        except Exception:
            pass

    def closeEvent(self: "GLViewportWidget", e) -> None:
        self.shutdown()
        super().closeEvent(e)

    def _effective_sim_timer_interval_ms(self: "GLViewportWidget") -> int:
        ms = int(self._loop.sim_timer_interval_ms)
        if ms > 0:
            return ms
        hz = max(1.0, float(self._loop.sim_hz))
        return max(1, int(round(1000.0 / hz)))

    def _effective_render_timer_interval_ms(self: "GLViewportWidget") -> int:
        ms = int(self._loop.render_timer_interval_ms)
        if ms > 0:
            return ms
        hz = max(120.0, float(self._loop.sim_hz))
        return max(1, int(round(1000.0 / hz)))
