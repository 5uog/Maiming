# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget

from ....math import mat4
from ....math.scalars import clampf
from ....math.transform_matrices import rotate_z_deg_matrix
from ....math.vec3 import Vec3
from ....math.view_angles import forward_from_yaw_pitch_deg
from ..controllers import settings_controller

if TYPE_CHECKING:
    from ..gl_viewport_widget import GLViewportWidget

_PLAYER_NAME_VERTICAL_OFFSET = 0.24
_PLAYER_NAME_CROUCH_OFFSET = 0.12
_PLAYER_NAME_OCCLUDED_OPACITY = 0.45
_PLAYER_NAME_CROUCH_OPACITY = 0.45
_PLAYER_NAME_SCREEN_MARGIN_PX = 8


class ViewportOverlayMixin:

    def set_hud(self: "GLViewportWidget", hud) -> None:
        self._hud = hud
        self._hud.setParent(self)
        self._hud.setGeometry(0, 0, max(1, self.width()), max(1, self.height()))
        self._sync_gameplay_hud_visibility()

    def fullscreen_enabled(self: "GLViewportWidget") -> bool:
        return bool(self._state.fullscreen)

    def _invalidate_pause_preview_cache(self: "GLViewportWidget") -> None:
        self._pause_preview_cache_key = None
        self._pause_preview_frame = QImage()

    def _clear_pause_preview_frame(self: "GLViewportWidget") -> None:
        if self._pause_preview_cache_key is None and self._pause_preview_frame.isNull():
            return
        self._invalidate_pause_preview_cache()
        self._overlay.set_player_preview_frame(QImage())
        self._overlay.set_player_preview_name_tag("", visible=False)

    def _position_detached_overlay_window(self: "GLViewportWidget", overlay: QWidget | None) -> None:
        if overlay is None:
            return
        if hasattr(overlay, "prepare_to_show"):
            overlay.prepare_to_show()
        host = self.window()
        overlay.adjustSize()
        size = overlay.size()
        if host is None:
            return
        frame = host.frameGeometry()
        x = int(frame.x() + max(0, (frame.width() - size.width()) // 2))
        y = int(frame.y() + max(0, (frame.height() - size.height()) // 2))
        overlay.move(int(x), int(y))

    def _position_settings_window(self: "GLViewportWidget") -> None:
        self._position_detached_overlay_window(self._settings)

    def _position_othello_settings_window(self: "GLViewportWidget") -> None:
        self._position_detached_overlay_window(self._othello_settings)

    @staticmethod
    def _pause_preview_key(*, player_state, width: int, height: int, device_pixel_ratio: float) -> tuple[object, ...] | None:
        if player_state is None:
            return None
        return (int(width), int(height), round(float(device_pixel_ratio), 4), round(float(player_state.base_x), 4), round(float(player_state.base_y), 4), round(float(player_state.base_z), 4), round(float(player_state.body_yaw_deg), 4), round(float(player_state.head_yaw_deg), 4), round(float(player_state.head_pitch_deg), 4), round(float(player_state.limb_phase_rad), 4), round(float(player_state.limb_swing_amount), 4), round(float(player_state.crouch_amount), 4), bool(player_state.is_first_person))

    def _build_pause_preview_player_state(self: "GLViewportWidget", player_state) -> object:
        body_yaw_deg, head_yaw_deg, head_pitch_deg = self._overlay.player_preview_angles()
        if player_state is None:
            return None
        return replace(player_state, base_x=0.0, base_y=-0.22, base_z=0.0, body_yaw_deg=float(body_yaw_deg), head_yaw_deg=float(head_yaw_deg), head_pitch_deg=float(head_pitch_deg), is_first_person=False)

    def _update_pause_preview_frame(self: "GLViewportWidget", player_state, *, fb_w: int, fb_h: int, dpr: float) -> None:
        if not bool(self._overlays.paused()) or bool(self.loading_active()):
            self._clear_pause_preview_frame()
            return
        self._sync_player_name_overlays()
        preview_widget = self._overlay._skin_preview
        if int(preview_widget.width()) <= 1 or int(preview_widget.height()) <= 1:
            self._clear_pause_preview_frame()
            return
        w = max(1, int(round(float(preview_widget.width()) * max(1.0, float(dpr)))))
        h = max(1, int(round(float(preview_widget.height()) * max(1.0, float(dpr)))))
        preview_state = self._build_pause_preview_player_state(player_state)
        preview_key = self._pause_preview_key(player_state=preview_state, width=int(w), height=int(h), device_pixel_ratio=float(dpr))
        if preview_key is not None and self._pause_preview_cache_key == preview_key and not self._pause_preview_frame.isNull():
            self._overlay.set_player_preview_frame(self._pause_preview_frame)
            return
        frame = self._renderer.render_player_preview_frame(w=int(w), h=int(h), player_state=preview_state, restore_framebuffer=int(self.defaultFramebufferObject()), restore_viewport=(0, 0, int(fb_w), int(fb_h)), device_pixel_ratio=float(max(1.0, float(dpr))))
        self._pause_preview_cache_key = preview_key
        self._pause_preview_frame = QImage(frame)
        self._overlay.set_player_preview_frame(frame)

    def _layout_viewport_overlays(self: "GLViewportWidget", *, width: int, height: int) -> None:
        if self._hud is not None:
            self._hud.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._othello_hud.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._overlay.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._crosshair.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._hotbar.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._inventory.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._death.setGeometry(0, 0, max(1, int(width)), max(1, int(height)))
        self._sync_player_name_overlays()

    def _restore_overlay_stack_after_resize(self: "GLViewportWidget") -> None:
        if self._overlays.dead():
            self._death.raise_()
        elif self._overlays.othello_settings_open():
            if self._othello_settings.isVisible():
                self._position_othello_settings_window()
                self._othello_settings.raise_()
        elif self._overlays.settings_open():
            if self._settings.isVisible():
                self._position_settings_window()
                self._settings.raise_()
        elif self._overlays.paused():
            self._overlay.raise_()
        elif self._overlays.inventory_open():
            self._inventory.raise_()
        self._sync_gameplay_hud_visibility()

    def _gameplay_hud_active(self: "GLViewportWidget") -> bool:
        return ((not bool(self.loading_active())) and (not bool(self._state.hide_hud)) and (not self._overlays.dead()) and (not self._overlays.paused()) and (not self._overlays.othello_settings_open()) and (not self._overlays.inventory_open()))

    def _debug_hud_active(self: "GLViewportWidget") -> bool:
        return bool(self._state.hud_visible) and bool(self._gameplay_hud_active())

    def _sync_gameplay_hud_visibility(self: "GLViewportWidget") -> None:
        show_gameplay_hud = bool(self._gameplay_hud_active())
        show_othello_hud = bool((not bool(self.loading_active())) and (not bool(self._state.hide_hud)) and (not self._overlays.dead()) and (not self._overlays.paused()) and (not self._overlays.inventory_open()) and (not self._overlays.settings_open()) and self._state.is_othello_space() and (not bool(self._state.hud_visible)))
        show_crosshair = bool(show_gameplay_hud and self._state.is_first_person_view())

        self._crosshair.setVisible(bool(show_crosshair))
        self._hotbar.setVisible(bool(show_gameplay_hud))
        self._othello_hud.setVisible(bool(show_othello_hud))

        if self._hud is not None:
            self._hud.setVisible(bool(self._debug_hud_active()))
            if bool(self._debug_hud_active()):
                self._hud.raise_()

        if bool(show_gameplay_hud):
            self._hotbar.raise_()
            if bool(show_crosshair):
                self._crosshair.raise_()
            if self._hud is not None and bool(self._debug_hud_active()):
                self._hud.raise_()
        if bool(show_othello_hud):
            self._othello_hud.raise_()
        self._audio.set_ambient_active(current_space_id=self._state.current_space_id, enabled=bool(show_gameplay_hud))
        self._sync_player_name_overlays()

    def _set_dead_overlay(self: "GLViewportWidget", on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
        self._overlays.set_dead(bool(on))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_paused_overlay(self: "GLViewportWidget", on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
        self._overlays.set_paused(bool(on))
        self._invalidate_pause_preview_cache()
        if not bool(on):
            self._overlay.set_player_preview_frame(QImage())
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_settings_overlay(self: "GLViewportWidget", on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
            if bool(self._state.fullscreen):
                self.fullscreen_changed.emit(False)
            self._position_settings_window()
        self._overlays.set_settings_open(bool(on))
        if (not bool(on)) and (not self._overlays.settings_open()) and (not self._overlays.othello_settings_open()):
            self.fullscreen_changed.emit(bool(self._state.fullscreen))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_othello_settings_overlay(self: "GLViewportWidget", on: bool) -> None:
        if bool(on):
            self._reset_held_mouse_actions()
            if bool(self._state.fullscreen):
                self.fullscreen_changed.emit(False)
            self._position_othello_settings_window()
        self._overlays.set_othello_settings_open(bool(on))
        if (not bool(on)) and (not self._overlays.settings_open()) and (not self._overlays.othello_settings_open()):
            self.fullscreen_changed.emit(bool(self._state.fullscreen))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _set_inventory_overlay(self: "GLViewportWidget", on: bool) -> None:
        if bool(on) and not settings_controller.inventory_available(self):
            return
        if bool(on):
            self._reset_held_mouse_actions()
        self._overlays.set_inventory_open(bool(on))
        self._sync_gameplay_hud_visibility()
        settings_controller.sync_cloud_motion_pause(self)

    def _hide_world_player_name_tag(self: "GLViewportWidget") -> None:
        self._player_name_tag.setVisible(False)

    def _set_world_player_name_tag(self: "GLViewportWidget", *, text: str, center_x: float, bottom_y: float, opacity: float) -> None:
        body = str(text).strip()
        if not body:
            self._hide_world_player_name_tag()
            return
        self._player_name_tag.setText(body)
        self._player_name_tag.adjustSize()
        label_w = int(max(1, self._player_name_tag.width()))
        label_h = int(max(1, self._player_name_tag.height()))
        margin = int(max(0, _PLAYER_NAME_SCREEN_MARGIN_PX))
        x = int(round(float(center_x) - float(label_w) * 0.5))
        y = int(round(float(bottom_y) - float(label_h)))
        x = max(int(margin), min(max(int(margin), int(self.width()) - label_w - int(margin)), int(x)))
        y = max(int(margin), min(max(int(margin), int(self.height()) - label_h - int(margin)), int(y)))
        self._player_name_tag_effect.setOpacity(float(clampf(float(opacity), 0.0, 1.0)))
        self._player_name_tag.setGeometry(int(x), int(y), int(label_w), int(label_h))
        self._player_name_tag.setVisible(True)
        self._player_name_tag.raise_()

    def _world_player_name_visible(self: "GLViewportWidget") -> bool:
        return bool((not bool(self.loading_active())) and (not bool(self._state.hide_hud)) and (not self._overlays.dead()) and (not self._overlays.paused()) and (not self._overlays.settings_open()) and (not self._overlays.othello_settings_open()) and (not self._overlays.inventory_open()) and (not bool(self._state.is_first_person_view())))

    def _sync_player_name_overlays(self: "GLViewportWidget") -> None:
        text = str(self._state.resolved_player_name).strip()
        preview_visible = bool(self._overlays.paused()) and (not bool(self.loading_active())) and (not bool(self._state.hide_hud)) and bool(text)
        self._overlay.set_player_preview_name_tag(text, visible=bool(preview_visible), opacity=1.0)
        if not bool(self._world_player_name_visible()) or not bool(text):
            self._hide_world_player_name_tag()

    def _player_name_anchor_world_pos(self: "GLViewportWidget", *, snapshot) -> Vec3:
        player = self._session.player
        crouch_amount = clampf(float(snapshot.player_model.crouch_amount), 0.0, 1.0)
        y = float(snapshot.player_model.base_y) + float(player.height) + float(_PLAYER_NAME_VERTICAL_OFFSET) - float(_PLAYER_NAME_CROUCH_OFFSET) * float(crouch_amount)
        return Vec3(float(snapshot.player_model.base_x), float(y), float(snapshot.player_model.base_z))

    def _player_name_occluded(self: "GLViewportWidget", *, eye: Vec3, target: Vec3, distance: float) -> bool:
        if float(distance) <= 1e-4:
            return False
        direction = (target - eye).normalized()
        hit = self._session.pick_block(reach=float(distance) + 0.05, origin=eye, direction=direction)
        if hit is None:
            return False
        return bool(float(hit.t) + 1e-4 < float(distance) - 0.02)

    def _update_world_player_name_tag(self: "GLViewportWidget", *, snapshot, eye: Vec3, yaw_deg: float, pitch_deg: float, roll_deg: float) -> None:
        text = str(self._state.resolved_player_name).strip()
        if not bool(text) or not bool(self._world_player_name_visible()) or int(self.width()) <= 1 or int(self.height()) <= 1:
            self._hide_world_player_name_tag()
            return

        anchor = self._player_name_anchor_world_pos(snapshot=snapshot)
        to_anchor = anchor - eye
        distance = float(to_anchor.length())
        if float(distance) <= 1e-4:
            self._hide_world_player_name_tag()
            return

        forward = forward_from_yaw_pitch_deg(float(yaw_deg), float(pitch_deg))
        view = mat4.look_dir(eye, forward)
        if abs(float(roll_deg)) > 1e-6:
            view = mat4.mul(rotate_z_deg_matrix(float(roll_deg)), view)
        proj = mat4.perspective(float(snapshot.camera.fov_deg), float(self.width()) / max(float(self.height()), 1.0), 0.01, float(self._renderer._cfg.camera.z_far))
        clip = mat4.mul(proj, view) @ np.asarray([float(anchor.x), float(anchor.y), float(anchor.z), 1.0], dtype=np.float32)
        if float(clip[3]) <= 1e-6:
            self._hide_world_player_name_tag()
            return

        ndc_x = float(clip[0]) / float(clip[3])
        ndc_y = float(clip[1]) / float(clip[3])
        ndc_z = float(clip[2]) / float(clip[3])
        if float(ndc_x) < -1.1 or float(ndc_x) > 1.1 or float(ndc_y) < -1.1 or float(ndc_y) > 1.1 or float(ndc_z) < -1.1 or float(ndc_z) > 1.1:
            self._hide_world_player_name_tag()
            return

        center_x = (float(ndc_x) * 0.5 + 0.5) * float(self.width())
        bottom_y = (1.0 - (float(ndc_y) * 0.5 + 0.5)) * float(self.height())

        opacity = 1.0
        if bool(getattr(self, "_recent_crouch_held", False)):
            opacity *= float(_PLAYER_NAME_CROUCH_OPACITY)
        if self._player_name_occluded(eye=eye, target=anchor, distance=float(distance)):
            opacity *= float(_PLAYER_NAME_OCCLUDED_OPACITY)

        self._set_world_player_name_tag(text=text, center_x=float(center_x), bottom_y=float(bottom_y), opacity=float(opacity))
