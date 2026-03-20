# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt

from .....application.handlers.keybinds import ACTION_CLEAR_SELECTED_SLOT, ACTION_TOGGLE_CREATIVE_MODE, ACTION_TOGGLE_DEBUG_HUD, ACTION_TOGGLE_DEBUG_SHADOW, ACTION_TOGGLE_INVENTORY, action_for_key
from .....shared.domain.play_space import PLAY_SPACE_MY_WORLD, PLAY_SPACE_OTHELLO, is_my_world_space, normalize_play_space_id
from ...common import hotbar_index_from_key
from . import othello_controller, settings_controller

if TYPE_CHECKING:
    from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

    from ..gl_viewport_widget import GLViewportWidget

def bind_overlay_actions(viewport: "GLViewportWidget") -> None:
    viewport._overlay.resume_requested.connect(lambda: resume_from_overlay(viewport))
    viewport._overlay.settings_requested.connect(lambda: open_settings_from_pause(viewport))
    viewport._overlay.play_my_world_requested.connect(lambda: switch_play_space(viewport, PLAY_SPACE_MY_WORLD, resume=True))
    viewport._overlay.play_othello_requested.connect(lambda: switch_play_space(viewport, PLAY_SPACE_OTHELLO, resume=True))
    viewport._death.respawn_requested.connect(lambda: respawn(viewport))
    viewport._inventory.block_selected.connect(lambda block_id: on_inventory_selected(viewport, str(block_id)))
    viewport._inventory.hotbar_slot_selected.connect(lambda slot_index: settings_controller.select_hotbar_slot(viewport, int(slot_index)))
    viewport._inventory.hotbar_slot_assigned.connect(lambda slot_index, item_id: settings_controller.assign_hotbar_slot(viewport, int(slot_index), str(item_id)))
    viewport._inventory.closed.connect(lambda: on_inventory_closed(viewport))

def respawn(viewport: "GLViewportWidget") -> None:
    viewport._session.respawn()
    viewport._invalidate_selection_target()
    viewport._renderer.clear_selection()
    viewport._set_dead_overlay(False)

def resume_from_overlay(viewport: "GLViewportWidget") -> None:
    viewport._set_paused_overlay(False)
    settings_controller.sync_cloud_motion_pause(viewport)

def switch_play_space(viewport: "GLViewportWidget", space_id: str, *, resume: bool = False) -> None:
    normalized = normalize_play_space_id(space_id)
    if normalized == normalize_play_space_id(viewport._state.current_space_id):
        if resume:
            resume_from_overlay(viewport)
        return

    othello_controller.clear_state_for_space_switch(viewport)
    viewport._state.current_space_id = normalized
    viewport._state.normalize()
    viewport._session = viewport._sessions.set_active_space(normalized)
    viewport._overlay.set_current_space(normalized)
    viewport._upload.reset(viewport._renderer)
    viewport._invalidate_selection_target()
    viewport._renderer.clear_selection()
    settings_controller.sync_hotbar_widgets(viewport)
    settings_controller.sync_first_person_target(viewport)
    othello_controller.sync_hud_text(viewport)
    viewport._sync_gameplay_hud_visibility()

    if resume:
        resume_from_overlay(viewport)

    othello_controller.maybe_request_ai(viewport)

def open_settings_from_pause(viewport: "GLViewportWidget") -> None:
    settings_controller.sync_settings_values(viewport)
    viewport._set_settings_overlay(True)
    settings_controller.sync_cloud_motion_pause(viewport)

def back_from_settings(viewport: "GLViewportWidget") -> None:
    settings_controller.sync_settings_values(viewport)
    viewport._set_settings_overlay(False)
    settings_controller.sync_cloud_motion_pause(viewport)

def open_othello_settings_from_item(viewport: "GLViewportWidget") -> None:
    othello_controller.sync_settings_values(viewport)
    viewport._set_othello_settings_overlay(True)
    settings_controller.sync_cloud_motion_pause(viewport)

def back_from_othello_settings(viewport: "GLViewportWidget") -> None:
    viewport._set_othello_settings_overlay(False)
    settings_controller.sync_cloud_motion_pause(viewport)

def on_inventory_selected(viewport: "GLViewportWidget", block_id: str) -> None:
    if not bool(viewport._state.creative_mode) or not settings_controller.inventory_available(viewport):
        return

    active_index = viewport._state.active_hotbar_index()
    viewport._state.set_hotbar_slot(int(active_index), str(block_id))
    settings_controller.sync_hotbar_widgets(viewport)
    settings_controller.sync_first_person_target(viewport)

def on_inventory_closed(viewport: "GLViewportWidget") -> None:
    viewport._set_inventory_overlay(False)

def handle_key_press(viewport: "GLViewportWidget", e: "QKeyEvent") -> bool:
    bound_action = action_for_key(int(e.key()), viewport._state.keybinds)
    hotbar_idx = hotbar_index_from_key(int(e.key()), viewport._state.keybinds)

    if (hotbar_idx is not None and not viewport._overlays.paused() and not viewport._overlays.dead() and not viewport._overlays.settings_open() and not viewport._overlays.othello_settings_open()):
        if not viewport._overlays.inventory_open():
            settings_controller.select_hotbar_slot(viewport, int(hotbar_idx))
            return True

    if bound_action == ACTION_TOGGLE_DEBUG_SHADOW:
        viewport._state.debug_shadow = not bool(viewport._state.debug_shadow)
        viewport._renderer.set_debug_shadow(bool(viewport._state.debug_shadow))
        return True

    if bound_action == ACTION_TOGGLE_DEBUG_HUD:
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
            back_from_othello_settings(viewport)
            return True
        if viewport._overlays.settings_open():
            back_from_settings(viewport)
            return True
        if viewport._overlays.paused():
            viewport._set_paused_overlay(False)
            settings_controller.sync_cloud_motion_pause(viewport)
        else:
            settings_controller.sync_settings_values(viewport)
            viewport._overlay.set_current_space(viewport._state.current_space_id)
            viewport._set_paused_overlay(True)
            settings_controller.sync_cloud_motion_pause(viewport)
        return True

    if bound_action == ACTION_TOGGLE_CREATIVE_MODE and not viewport._overlays.paused() and not viewport._overlays.dead():
        settings_controller.set_creative_mode(viewport, not viewport._state.creative_mode)
        settings_controller.sync_settings_values(viewport)
        return True

    if bound_action == ACTION_TOGGLE_INVENTORY and not viewport._overlays.paused() and not viewport._overlays.dead():
        if settings_controller.inventory_available(viewport):
            viewport._set_inventory_overlay(not viewport._overlays.inventory_open())
        return True

    if (bound_action == ACTION_CLEAR_SELECTED_SLOT and is_my_world_space(viewport._state.current_space_id) and not viewport._overlays.paused() and not viewport._overlays.inventory_open() and not viewport._overlays.dead() and not viewport._overlays.settings_open() and not viewport._overlays.othello_settings_open()):
        settings_controller.clear_selected_hotbar_slot(viewport)
        return True

    if (not viewport._overlays.paused() and not viewport._overlays.inventory_open() and not viewport._overlays.dead() and not viewport._overlays.othello_settings_open()):
        viewport._inp.on_key_press(e)
    return False


def handle_wheel(viewport: "GLViewportWidget", e: "QWheelEvent") -> bool:
    if (viewport._overlays.paused() or viewport._overlays.inventory_open() or viewport._overlays.dead() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open()):
        return False

    delta_y = int(e.angleDelta().y())
    if delta_y > 0:
        settings_controller.cycle_hotbar(viewport, -1)
        e.accept()
        return True
    if delta_y < 0:
        settings_controller.cycle_hotbar(viewport, 1)
        e.accept()
        return True
    return False

def handle_mouse_press(viewport: "GLViewportWidget", e: "QMouseEvent") -> bool:
    viewport.setFocus(Qt.FocusReason.MouseFocusReason)

    if (viewport._overlays.paused() or viewport._overlays.inventory_open() or viewport._overlays.dead() or viewport._overlays.settings_open() or viewport._overlays.othello_settings_open()):
        return False

    if not viewport._inp.captured():
        viewport._inp.set_mouse_capture(True)
        return False

    snapshot = viewport._make_render_snapshot()
    render_eye, _yaw, _pitch, _roll, render_direction = viewport._effective_camera_from_snapshot(snapshot)

    if viewport._state.is_othello_space():
        if e.button() == Qt.MouseButton.LeftButton:
            othello_controller.handle_left_click(viewport, render_eye, render_direction)
        elif e.button() == Qt.MouseButton.RightButton:
            othello_controller.handle_right_click(viewport)
        return True

    if e.button() == Qt.MouseButton.LeftButton:
        break_outcome = None
        if bool(viewport._state.creative_mode) and is_my_world_space(viewport._state.current_space_id):
            break_outcome = viewport._session.break_block(reach=float(viewport._state.reach), origin=render_eye, direction=render_direction)
        viewport._first_person_motion.trigger_left_swing()
        if break_outcome is not None and bool(break_outcome.success):
            viewport._audio.play_interaction(action=break_outcome.action, block_state=break_outcome.target_block_state, position=break_outcome.target_position)
            viewport._invalidate_selection_target()
        return True

    if e.button() == Qt.MouseButton.RightButton:
        outcome = viewport._session.place_block(block_id=settings_controller.current_block_id(viewport), reach=float(viewport._state.reach), crouching=bool(viewport._inp.crouch_held()), origin=render_eye, direction=render_direction)
        viewport._first_person_motion.trigger_right_swing(success=bool(outcome.success))
        if bool(outcome.success):
            viewport._audio.play_interaction(action=outcome.action, block_state=outcome.target_block_state, position=outcome.target_position)
            viewport._invalidate_selection_target()
        return True

    return False