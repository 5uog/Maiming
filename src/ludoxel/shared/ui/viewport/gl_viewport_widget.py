# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QImage, QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel

from ....application.audio import AudioManager
from ....application.runtime.context.play_space_context import PlaySpaceContext
from ....application.runtime.state.runtime_preferences import RuntimePreferences
from ....application.runtime.tasks.fixed_step_runner import FixedStepRunner
from ....application.runtime.tasks.state_persistence import apply_persisted_state_if_present
from ....features.othello.application.othello_match_controller import OthelloMatchController
from ....features.othello.domain.engine.ai_worker import OthelloAiWorker
from ....features.othello.domain.game.types import OthelloAnalysis
from ....features.othello.ui.hud_widget import OthelloHudWidget
from ....features.othello.ui.settings_overlay import OthelloSettingsOverlay
from ....features.othello.ui.viewport import othello_controller
from ...opengl.runtime.gl_renderer import GLRenderer
from ...rendering.first_person_motion import FirstPersonMotionController
from ..config.game_loop_params import DEFAULT_GAME_LOOP_PARAMS, GameLoopParams
from ..config.gl_surface_format import build_gl_surface_format
from ..hud.crosshair_widget import CrosshairWidget
from ..hud.hud_controller import HudController
from ..hud.hotbar_widget import HotbarWidget
from ..common.status_overlay import status_overlay_title_image_path
from ..overlays.death_overlay import DeathOverlay
from ..overlays.inventory_overlay import InventoryOverlay
from ..overlays.pause_overlay import PauseOverlay
from ..qt_input_adapter import QtInputAdapter
from ..settings.settings_overlay import SettingsOverlay
from .controllers import interaction_controller, settings_controller
from .runtime import OverlayRefs, ViewportFrameSync, ViewportInput, ViewportLifecycleMixin, ViewportOverlayMixin, ViewportOverlays, ViewportRenderLoopMixin, ViewportSelectionState, ViewportStateMixin, WorldUploadTracker

_APPLICATION_DEACTIVATION_PAUSE_DELAY_MS = 250


class GLViewportWidget(ViewportRenderLoopMixin, ViewportStateMixin, ViewportOverlayMixin, ViewportLifecycleMixin, QOpenGLWidget):
    hud_updated = pyqtSignal(object)
    fullscreen_changed = pyqtSignal(bool)
    loading_state_changed = pyqtSignal(bool)
    loading_status_changed = pyqtSignal(str)
    loading_finished = pyqtSignal()

    def __init__(self, project_root: Path, resource_root: Path, parent=None, loop_params: GameLoopParams=DEFAULT_GAME_LOOP_PARAMS, launch_player_name: str | None = None) -> None:
        super().__init__(parent)

        self._project_root = Path(project_root)
        self._resource_root = Path(resource_root)
        self._assets_dir = self._resource_root / "assets"
        self._loop = loop_params

        self._adapter = QtInputAdapter(self)
        self._inp = ViewportInput(widget=self, adapter=self._adapter)

        self._sessions = PlaySpaceContext.create_default(seed=0)
        self._session = self._sessions.active_session()
        self._runner = FixedStepRunner(step_dt=self._loop.step_dt(), on_step=self._on_step)

        self._renderer = GLRenderer()
        self._hud = None
        self._othello_hud = OthelloHudWidget(self)
        self._othello_hud.setVisible(False)
        self._player_name_tag = QLabel(self)
        self._player_name_tag.setObjectName("playerNameTag")
        self._player_name_tag.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._player_name_tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._player_name_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._player_name_tag.setVisible(False)
        self._player_name_tag_effect = QGraphicsOpacityEffect(self._player_name_tag)
        self._player_name_tag_effect.setOpacity(1.0)
        self._player_name_tag.setGraphicsEffect(self._player_name_tag_effect)

        self._upload = WorldUploadTracker()
        self._hud_ctl = HudController()

        self._state = RuntimePreferences()
        settings_controller.sync_state_from_renderer_sun(self)
        self._first_person_motion = FirstPersonMotionController(slim_arm=True)

        self._selection_state = ViewportSelectionState()
        self._othello_match = OthelloMatchController()
        self._othello_ai = OthelloAiWorker(self)
        self._othello_hover_square: int | None = None
        self._pending_othello_ai_result: tuple[int, int | None] | None = None
        self._othello_ai_request_armed: bool = False
        self._othello_title_flash_text: str = ""
        self._othello_title_flash_until_s: float = 0.0
        self._last_othello_message: str = ""
        self._othello_hud_signature: tuple[object, ...] | None = None
        self._othello_render_state_cache_key: tuple[object, ...] | None = None
        self._othello_render_state_cache = None
        self._othello_analysis = OthelloAnalysis().normalized()
        self._othello_analysis_request_signature: tuple[object, ...] | None = None
        self._othello_book_learning_running: bool = False
        self._othello_book_learning_status_text: str = ""
        self._othello_book_summary_text: str = ""
        self._othello_book_learning_progress: dict[str, object] | None = None
        self._othello_last_passive_hud_sync_s: float = 0.0

        self._last_paint_ms: float = 0.0
        self._last_selection_pick_ms: float = 0.0
        self._shutdown_done = False
        self._gl_initialized = False
        self._runtime_active = False
        self._frame_sync = ViewportFrameSync()
        self._player_skin_image = QImage()
        self._pause_preview_cache_key: tuple[object, ...] | None = None
        self._pause_preview_frame = QImage()
        self._block_break_particles = ()
        self._left_mouse_held: bool = False
        self._right_mouse_held: bool = False
        self._left_mouse_repeat_due_s: float = 0.0
        self._right_mouse_repeat_due_s: float = 0.0
        self._right_mouse_repeat_enabled: bool = False
        self._right_mouse_repeat_mode: str | None = None
        self._right_mouse_repeat_target_cell: tuple[int, int, int] | None = None
        self._right_mouse_repeat_line_start: tuple[int, int, int] | None = None
        self._right_mouse_repeat_line_step: tuple[int, int, int] | None = None
        self._right_mouse_repeat_line_face: int | None = None
        self._right_mouse_repeat_line_plane_normal: tuple[int, int, int] | None = None
        self._right_mouse_repeat_line_plane_point: tuple[float, float, float] | None = None
        self._right_mouse_repeat_line_min_progress: int = 0
        self._right_mouse_repeat_line_max_progress: int = 0
        self._right_mouse_repeat_line_start_cell_materialized: bool = True
        self._right_mouse_repeat_line_pending_support_cell: tuple[int, int, int] | None = None
        self._right_mouse_repeat_line_pending_support_face: int | None = None
        self._right_mouse_repeat_line_pending_support_hit_point: tuple[float, float, float] | None = None
        self._right_mouse_repeat_support_face_mode: bool = False
        self._right_mouse_repeat_visible_face_chain_mode: bool = False
        self._right_mouse_repeat_origin_player_y: float = 0.0
        self._right_mouse_repeat_vertical_lock_sign: int = 0
        self._recent_move_f: float = 0.0
        self._recent_move_s: float = 0.0
        self._recent_jump_held: bool = False
        self._recent_jump_pressed: bool = False
        self._recent_crouch_held: bool = False
        self._recent_vertical_motion_sign: int = 0
        app = QGuiApplication.instance()
        self._application_active = bool(app is None or app.applicationState() == Qt.ApplicationState.ApplicationActive)

        self._overlay = PauseOverlay(self)
        self._overlay.set_title_image_path(status_overlay_title_image_path(self._resource_root))
        self._settings = SettingsOverlay(None, resource_root=self._resource_root, as_window=True)
        self._othello_settings = OthelloSettingsOverlay(None, as_window=True)
        self._death = DeathOverlay(self)

        self._crosshair = CrosshairWidget(self)
        self._crosshair.setVisible(False)

        self._hotbar = HotbarWidget(parent=self, resource_root=self._resource_root, registry=self._session.block_registry)
        self._hotbar.setVisible(False)

        self._inventory = InventoryOverlay(parent=self, resource_root=self._resource_root, registry=self._session.block_registry)

        self._overlays = ViewportOverlays(refs=OverlayRefs(pause=self._overlay, settings=self._settings, othello_settings=self._othello_settings, inventory=self._inventory, death=self._death, crosshair=self._crosshair, hotbar=self._hotbar, hud_getter=lambda: self._hud, othello_hud_getter=lambda: self._othello_hud), runner=self._runner, inp=self._inp)
        self._overlay.preview_changed.connect(self._invalidate_pause_preview_cache)
        self._overlay.preview_changed.connect(self.update)
        settings_controller.bind_settings_overlay(self)
        othello_controller.bind_othello_controls(self)
        interaction_controller.bind_overlay_actions(self)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

        self._sim_timer = QTimer(self)
        self._sim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._sim_timer.setInterval(int(self._effective_sim_timer_interval_ms()))
        self._sim_timer.timeout.connect(self._tick_sim)

        self._render_timer = QTimer(self)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._render_timer.setInterval(int(self._effective_render_timer_interval_ms()))
        self._render_timer.timeout.connect(self.update)
        self.frameSwapped.connect(self._on_frame_swapped)
        self._deactivation_pause_timer = QTimer(self)
        self._deactivation_pause_timer.setSingleShot(True)
        self._deactivation_pause_timer.setInterval(int(_APPLICATION_DEACTIVATION_PAUSE_DELAY_MS))
        self._deactivation_pause_timer.timeout.connect(self._pause_after_application_deactivation)
        self._pause_on_application_deactivation = False

        self.setFormat(build_gl_surface_format(vsync_on=False))

        self._state, persisted_othello_state = apply_persisted_state_if_present(project_root=self._project_root, sessions=self._sessions, renderer=self._renderer)
        if launch_player_name is not None:
            self._state.player_name = str(launch_player_name)
        self._session = self._sessions.set_active_space(self._state.current_space_id)
        self._othello_match.set_default_settings(self._state.othello_settings)
        self._othello_match.set_game_state(persisted_othello_state)
        self._overlay.set_current_space(self._state.current_space_id)
        self._audio = AudioManager(resource_root=self._resource_root, block_registry=self._session.block_registry, parent=self)

        settings_controller.refresh_player_identity(self, regenerate_if_blank=True)
        settings_controller.apply_runtime_to_renderer(self)
        settings_controller.sync_input_bindings(self)
        settings_controller.sync_audio_preferences(self)
        settings_controller.sync_hotbar_widgets(self)
        settings_controller.sync_crosshair_widgets(self)
        settings_controller.sync_player_skin(self)
        settings_controller.sync_first_person_target(self)
        settings_controller.sync_view_model_visibility(self)
        othello_controller.sync_settings_values(self)
        othello_controller.sync_hud_text(self)
        self._sync_gameplay_hud_visibility()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state_changed)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        if interaction_controller.handle_key_press(self, e):
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        self._inp.on_key_release(e)
        super().keyReleaseEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        if interaction_controller.handle_wheel(self, e):
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        interaction_controller.handle_mouse_press(self, e)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if bool(self.loading_active()):
            e.accept()
            return
        interaction_controller.handle_mouse_release(self, e)
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if bool(self.loading_active()) or (self._overlays.paused() or self._overlays.inventory_open() or self._overlays.dead() or self._overlays.settings_open() or self._overlays.othello_settings_open() or (not self._inp.captured())):
            super().mouseMoveEvent(e)
            return
        e.accept()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self.arm_resume_refresh()
        settings_controller.sync_cloud_motion_pause(self)
        self._sync_runtime_activity()

    def hideEvent(self, e) -> None:
        self._set_runtime_active(False)
        settings_controller.sync_cloud_motion_pause(self)
        super().hideEvent(e)
