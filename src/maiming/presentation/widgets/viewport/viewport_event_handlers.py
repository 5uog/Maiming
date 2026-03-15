# FILE: src/maiming/presentation/widgets/viewport/viewport_event_handlers.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt

from ....domain.play_space import PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO, normalize_play_space_id
from ..common import hotbar_index_from_key
from . import viewport_othello_controller, viewport_settings_controller

if TYPE_CHECKING:
    from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

    from .gl_viewport_widget import GLViewportWidget

def bind_overlay_actions(viewport: "GLViewportWidget") -> None:
    viewport._overlay.resume_requested.connect(viewport._resume_from_overlay)
    viewport._overlay.settings_requested.connect(viewport._open_settings_from_pause)
    viewport._overlay.play_my_world_requested.connect(lambda: viewport._switch_play_space(PLAY_SPACE_MY_WORLD, resume=True))
    viewport._overlay.play_othello_requested.connect(lambda: viewport._switch_play_space(PLAY_SPACE_OTHELLO, resume=True))
    viewport._death.respawn_requested.connect(viewport._respawn)
    viewport._inventory.block_selected.connect(viewport._on_inventory_selected)
    viewport._inventory.hotbar_slot_selected.connect(viewport._select_hotbar_slot)
    viewport._inventory.hotbar_slot_assigned.connect(viewport._assign_hotbar_slot)
    viewport._inventory.closed.connect(viewport._on_inventory_closed)

def respawn(viewport: "GLViewportWidget") -> None:
    viewport._session.respawn()
    viewport._invalidate_selection_target()
    viewport._renderer.clear_selection()
    viewport._set_dead_overlay(False)

def resume_from_overlay(viewport: "GLViewportWidget") -> None:
    viewport._set_paused_overlay(False)
    viewport_settings_controller.sync_cloud_motion_pause(viewport)

def switch_play_space(viewport: "GLViewportWidget", space_id: str, *, resume: bool = False) -> None:
    normalized = normalize_play_space_id(space_id)
    if normalized == normalize_play_space_id(viewport._state.current_space_id):
        if resume:
            resume_from_overlay(viewport)
        return

    viewport_othello_controller.clear_state_for_space_switch(viewport)
    viewport._state.current_space_id = normalized
    viewport._state.normalize()
    viewport._session = viewport._sessions.set_active_space(normalized)
    viewport._overlay.set_current_space(normalized)
    viewport._upload.reset(viewport._renderer)
    viewport._invalidate_selection_target()
    viewport._renderer.clear_selection()
    viewport_settings_controller.sync_hotbar_widgets(viewport)
    viewport_settings_controller.sync_first_person_target(viewport)
    viewport_othello_controller.sync_hud_text(viewport)
    viewport._sync_gameplay_hud_visibility()

    if resume:
        resume_from_overlay(viewport)

    viewport_othello_controller.maybe_request_ai(viewport)

def open_settings_from_pause(viewport: "GLViewportWidget") -> None:
    viewport_settings_controller.sync_settings_values(viewport)
    viewport._set_settings_overlay(True)
    viewport_settings_controller.sync_cloud_motion_pause(viewport)

def back_from_settings(viewport: "GLViewportWidget") -> None:
    viewport_settings_controller.sync_settings_values(viewport)
    viewport._set_settings_overlay(False)
    viewport_settings_controller.sync_cloud_motion_pause(viewport)

def open_othello_settings_from_item(viewport: "GLViewportWidget") -> None:
    viewport_othello_controller.sync_settings_values(viewport)
    viewport._set_othello_settings_overlay(True)
    viewport_settings_controller.sync_cloud_motion_pause(viewport)

def back_from_othello_settings(viewport: "GLViewportWidget") -> None:
    viewport._set_othello_settings_overlay(False)
    viewport_settings_controller.sync_cloud_motion_pause(viewport)

def on_inventory_selected(viewport: "GLViewportWidget", block_id: str) -> None:
    if not bool(viewport._state.creative_mode) or not viewport_settings_controller.inventory_available(viewport):
        return
    active_index = int(viewport._state.creative_selected_hotbar_index if bool(viewport._state.creative_mode) else viewport._state.survival_selected_hotbar_index)
    viewport._state.set_hotbar_slot(int(active_index), str(block_id))
    viewport_settings_controller.sync_hotbar_widgets(viewport)
    viewport_settings_controller.sync_first_person_target(viewport)

def on_inventory_closed(viewport: "GLViewportWidget") -> None:
    viewport._set_inventory_overlay(False)

def handle_key_press(viewport: "GLViewportWidget", e: "QKeyEvent") -> bool:
    hotbar_idx = hotbar_index_from_key(int(e.key()))
    if hotbar_idx is not None and not viewport._overlays.paused() and not viewport._overlays.dead() and not viewport._overlays.settings_open() and not viewport._overlays.othello_settings_open():
        if not viewport._overlays.inventory_open():
            viewport._select_hotbar_slot(int(hotbar_idx))
            return True

    if int(e.key()) == int(Qt.Key.Key_F4):
        viewport._state.debug_shadow = not bool(viewport._state.debug_shadow)
        viewport._renderer.set_debug_shadow(bool(viewport._state.debug_shadow))
        return True

    if int(e.key()) == int(Qt.Key.Key_F3):
        viewport._state.hud_visible = not bool(viewport._state.hud_visible)
        viewport._sync_gameplay_hud_visibility()
        return True

    if int(e.key()) == int(Qt.Key.Key_Escape):
        if viewport._overlays.dead():
            return True
        if viewport._overlays.inventory_open():
            viewport._set_inventory_overlay(False)
            return True
        if viewport._overlays.othello_settings_open():
            viewport._back_from_othello_settings()
            return True
        if viewport._overlays.settings_open():
            viewport._back_from_settings()
            return True
        if viewport._overlays.paused():
            viewport._set_paused_overlay(False)
            viewport_settings_controller.sync_cloud_motion_pause(viewport)
        else:
            viewport_settings_controller.sync_settings_values(viewport)
            viewport._overlay.set_current_space(viewport._state.current_space_id)
            viewport._set_paused_overlay(True)
            viewport_settings_controller.sync_cloud_motion_pause(viewport)
        return True

    if int(e.key()) == int(Qt.Key.Key_B) and not viewport._overlays.paused() and not viewport._overlays.dead():
        viewport._set_creative_mode(not viewport._state.creative_mode)
        viewport_settings_controller.sync_settings_values(viewport)
        return True

    if int(e.key()) == int(Qt.Key.Key_E) and not viewport._overlays.paused() and not viewport._overlays.dead():
        if viewport_settings_controller.inventory_available(viewport):
            viewport._set_inventory_overlay(not viewport._overlays.inventory_open())
        return True

    if not viewport._overlays.paused() and not viewport._overlays.inventory_open() and not viewport._overlays.dead() and not viewport._overlays.othello_settings_open():
        viewport._inp.on_key_press(e)
    return False

def handle_wheel(viewport: "GLViewportWidget", e: "QWheelEvent") -> bool:
    if viewport._overlays.paused() or viewport._overlays.inventory_open() or viewport._overlays.dead() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open():
        return False

    delta_y = int(e.angleDelta().y())
    if delta_y > 0:
        viewport._cycle_hotbar(-1)
        e.accept()
        return True
    if delta_y < 0:
        viewport._cycle_hotbar(1)
        e.accept()
        return True
    return False

def handle_mouse_press(viewport: "GLViewportWidget", e: "QMouseEvent") -> bool:
    viewport.setFocus(Qt.FocusReason.MouseFocusReason)

    if viewport._overlays.paused() or viewport._overlays.inventory_open() or viewport._overlays.dead() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open():
        return False

    if not viewport._inp.captured():
        viewport._inp.set_mouse_capture(True)
        return False

    snapshot = viewport._make_render_snapshot()
    render_eye, _yaw, _pitch, _roll, render_direction = viewport._effective_camera_from_snapshot(snapshot)

    if viewport._state.is_othello_space():
        if e.button() == Qt.MouseButton.LeftButton:
            viewport_othello_controller.handle_left_click(viewport, render_eye, render_direction)
        elif e.button() == Qt.MouseButton.RightButton:
            viewport_othello_controller.handle_right_click(viewport)
        return True

    if e.button() == Qt.MouseButton.LeftButton:
        viewport._session.break_block(reach=float(viewport._state.reach), origin=render_eye, direction=render_direction)
        viewport._first_person_motion.trigger_left_swing()
        viewport._invalidate_selection_target()
        return True

    if e.button() == Qt.MouseButton.RightButton:
        success = viewport._session.place_block(block_id=viewport_settings_controller.current_block_id(viewport), reach=float(viewport._state.reach), crouching=bool(viewport._inp.crouch_held()), origin=render_eye, direction=render_direction)
        viewport._first_person_motion.trigger_right_swing(success=bool(success))
        if bool(success):
            viewport._invalidate_selection_target()
        return True

    return False