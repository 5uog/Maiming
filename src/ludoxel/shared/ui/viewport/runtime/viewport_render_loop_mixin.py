# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

import time

from PyQt6.QtWidgets import QMessageBox

from .....application.audio import PLAYER_EVENT_LAND, PLAYER_EVENT_STEP
from ....math.vec3 import Vec3
from ....rendering.player_render_state_composer import compose_player_render_state
from .....features.othello.ui.viewport import othello_controller
from ..controllers import interaction_controller, settings_controller

if TYPE_CHECKING:
                                                                from ..gl_viewport_widget import GLViewportWidget


class ViewportRenderLoopMixin:

    def _framebuffer_extent(self: "GLViewportWidget") -> tuple[int, int, float]:
        dpr = float(self.devicePixelRatioF())
        fb_w = max(1, int(round(float(self.width()) * dpr)))
        fb_h = max(1, int(round(float(self.height()) * dpr)))
        return (int(fb_w), int(fb_h), float(dpr))

    def _update_loading_progress_from_upload(self: "GLViewportWidget", *, eye: Vec3) -> None:
        if not bool(self.loading_active()):
            return
        ready_chunks, total_chunks = self._upload.visible_load_progress(world=self._session.world, eye=eye, render_distance_chunks=int(self._state.render_distance_chunks))
        if self._frame_sync.loading.set_progress(ready_chunks=int(ready_chunks), total_chunks=int(total_chunks)):
            if int(total_chunks) > 0:
                self._set_loading_status(f"Loading world... {int(ready_chunks)}/{int(total_chunks)} chunks")
            else:
                self._set_loading_status("Loading world...")
        if self._upload.visible_chunks_ready(world=self._session.world, eye=eye, render_distance_chunks=int(self._state.render_distance_chunks)):
            self._finish_loading()

    def _world_block_state(self: "GLViewportWidget", x: int, y: int, z: int) -> str | None:
        return self._session.world.blocks.get((int(x), int(y), int(z)))

    def _refresh_selection_for_frame(self: "GLViewportWidget", *, snapshot, interaction_eye: Vec3, interaction_yaw_deg: float, interaction_pitch_deg: float) -> None:
        if bool(self.loading_active()):
            return
        if self._state.is_othello_space():
            if self._selection_due(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg)):
                self._last_selection_pick_ms = 0.0
                self._invalidate_selection_target()
                self._renderer.clear_selection()
                othello_controller.refresh_hover_square(self, snapshot)
                self._mark_selection(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg))
            return

        self._othello_hover_square = None
        if not self._selection_due(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg)):
            return
        self._last_selection_pick_ms = self._selection_state.refresh(session=self._session, reach=float(self._state.reach), eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg))
        selection_target = self._selection_state.target()
        if selection_target is None:
            self._renderer.clear_selection()
        else:
            hx, hy, hz, st = selection_target
            self._renderer.set_selection_target(x=int(hx), y=int(hy), z=int(hz), state_str=str(st), get_state=self._world_block_state, world_revision=int(self._session.world.revision))
        self._mark_selection(eye=interaction_eye, yaw_deg=float(interaction_yaw_deg), pitch_deg=float(interaction_pitch_deg))

    @staticmethod
    def _othello_state_changed(state_before, state_after) -> bool:
        return bool(state_before.status != state_after.status or state_before.board != state_after.board or state_before.current_turn != state_after.current_turn or state_before.legal_moves != state_after.legal_moves or state_before.thinking != state_after.thinking or state_before.last_move_index != state_after.last_move_index or state_before.animations != state_after.animations or state_before.message != state_after.message or state_before.winner != state_after.winner)

    def _emit_debug_hud_payload(self: "GLViewportWidget") -> None:
        if not self._hud_ctl.should_emit() or not bool(self._debug_hud_active()):
            return
        fb_w, fb_h, dpr = self._framebuffer_extent()
        payload = self._hud_ctl.build_payload(session=self._session, renderer=self._renderer, auto_jump_enabled=self._state.auto_jump_enabled, auto_sprint_enabled=self._state.auto_sprint_enabled, creative_mode=self._state.creative_mode, flying=bool(self._session.player.flying), inventory_open=self._overlays.inventory_open(), selected_block_id=settings_controller.current_item_id(self) or "", reach=self._state.reach, sun_az_deg=self._state.sun_az_deg, sun_el_deg=self._state.sun_el_deg, shadow_enabled=self._state.shadow_enabled, world_wire=self._state.world_wire, cloud_wire=self._state.cloud_wire, cloud_enabled=self._state.cloud_enabled, cloud_density=self._state.cloud_density, cloud_seed=self._state.cloud_seed, debug_shadow=self._state.debug_shadow, fb_w=fb_w, fb_h=fb_h, dpr=dpr, vsync_on=self._state.vsync_on, render_timer_interval_ms=int(self._render_timer.interval()), sim_hz=float(self._loop.sim_hz), render_distance_chunks=int(self._state.render_distance_chunks), paint_ms=float(self._last_paint_ms), selection_pick_ms=float(self._last_selection_pick_ms))
        self.hud_updated.emit(payload)

    def initializeGL(self: "GLViewportWidget") -> None:
        self._begin_loading("Initializing renderer...")
        try:
            self._renderer.initialize(self._assets_dir, block_registry=self._session.block_registry)
        except Exception as exc:
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
            QMessageBox.critical(self, "OpenGL 4.3 initialization failed", str(exc).strip() if str(exc).strip() else "Unknown OpenGL initialization error.")
            raise

        ctx = self.context()
        if ctx is not None:
            try:
                self._state.vsync_on = int(ctx.format().swapInterval()) > 0
            except Exception:
                self._state.vsync_on = False

        self._frame_sync.reset_after_gl_initialize()

        self._sync_player_skin_design(push_to_renderer=True, context_current=True)
        settings_controller.apply_runtime_to_renderer(self)
        settings_controller.sync_input_bindings(self)
        settings_controller.sync_audio_preferences(self)
        settings_controller.sync_hotbar_widgets(self)
        settings_controller.sync_crosshair_widgets(self)
        settings_controller.sync_cloud_motion_pause(self)
        othello_controller.sync_hud_text(self)
        self._sync_gameplay_hud_visibility()
        self._gl_initialized = True
        self._begin_loading("Loading world...")
        self._sync_runtime_activity()

    def resizeGL(self: "GLViewportWidget", w: int, h: int) -> None:
        self._layout_viewport_overlays(width=int(w), height=int(h))
        self._restore_overlay_stack_after_resize()

    def paintGL(self: "GLViewportWidget") -> None:
        paint_t0 = time.perf_counter()
        self._hud_ctl.on_render_frame()
        self._inp.ensure_mouse_capture_applied()

        snapshot = self._make_render_snapshot()
        camera_snapshot = snapshot.camera
        upload_eye = Vec3(float(camera_snapshot.eye_x), float(camera_snapshot.eye_y), float(camera_snapshot.eye_z))
        render_eye, render_yaw_deg, render_pitch_deg, render_roll_deg, _render_direction = self._effective_camera_from_snapshot(snapshot)
        interaction_eye, interaction_yaw_deg, interaction_pitch_deg, _interaction_direction = self._interaction_pose_from_snapshot(snapshot)
        self._audio.cache_listener_pose(eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg))

        if self._upload_due(eye=upload_eye):
            self._upload.upload_if_needed(world=self._session.world, renderer=self._renderer, eye=upload_eye, render_distance_chunks=int(self._state.render_distance_chunks))
            self._mark_upload(eye=upload_eye)

        self._update_loading_progress_from_upload(eye=upload_eye)
        self._refresh_selection_for_frame(snapshot=snapshot, interaction_eye=interaction_eye, interaction_yaw_deg=float(interaction_yaw_deg), interaction_pitch_deg=float(interaction_pitch_deg))

        fb_w, fb_h, dpr = self._framebuffer_extent()
        player_state = compose_player_render_state(snapshot=snapshot, motion=self._first_person_motion.sample(), block_registry=self._session.block_registry, arm_rotation_limit_min_deg=float(self._state.arm_rotation_limit_min_deg), arm_rotation_limit_max_deg=float(self._state.arm_rotation_limit_max_deg))

        self._renderer.render(w=fb_w, h=fb_h, eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg), fov_deg=float(camera_snapshot.fov_deg), render_distance_chunks=int(self._state.render_distance_chunks), player_state=player_state, othello_state=othello_controller.build_render_state(self), falling_blocks=tuple(snapshot.falling_blocks), block_break_particles=tuple(snapshot.block_break_particles))
        self._update_world_player_name_tag(snapshot=snapshot, eye=render_eye, yaw_deg=float(render_yaw_deg), pitch_deg=float(render_pitch_deg), roll_deg=float(render_roll_deg))
        self._update_pause_preview_frame(player_state, fb_w=int(fb_w), fb_h=int(fb_h), dpr=float(dpr))
        self._last_paint_ms = float((time.perf_counter() - paint_t0) * 1000.0)

    def _tick_sim(self: "GLViewportWidget") -> None:
        if bool(self.loading_active()) or (self._overlays.dead() or self._overlays.paused() or self._overlays.settings_open() or self._overlays.othello_settings_open()):
            return
        self._runner.update()

    def _on_step(self: "GLViewportWidget", dt: float) -> None:
        othello_controller.consume_pending_ai_result(self)
        self._update_block_break_particles(float(dt))

        self._inp.poll_relative_mouse_delta()
        frame, mouse_delta = self._inp.consume(invert_x=self._state.invert_x, invert_y=self._state.invert_y)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        sprint = bool(frame.sprint)
        if bool(self._state.auto_sprint_enabled) and float(frame.move_f) > 1e-6 and (not bool(frame.crouch)):
            sprint = True

        self._recent_move_f = float(frame.move_f)
        self._recent_move_s = float(frame.move_s)
        self._recent_jump_held = bool(frame.jump_held)
        self._recent_jump_pressed = bool(frame.jump_pressed)
        self._recent_crouch_held = bool(frame.crouch)
        prev_player_y = float(self._session.player.position.y)
        interaction_controller.handle_held_mouse_buttons_pre_step(self)
        step_result = self._session.step(dt=float(dt), move_f=frame.move_f, move_s=frame.move_s, jump_held=bool(frame.jump_held), jump_pressed=bool(frame.jump_pressed), sprint=bool(sprint), crouch=bool(frame.crouch), mdx=float(mouse_delta.dx), mdy=float(mouse_delta.dy), creative_mode=bool(self._state.creative_mode), auto_jump_enabled=bool(self._state.auto_jump_enabled))
        delta_player_y = float(self._session.player.position.y) - float(prev_player_y)
        if float(delta_player_y) >= 1e-4:
            self._recent_vertical_motion_sign = 1
        elif float(delta_player_y) <= -1e-4:
            self._recent_vertical_motion_sign = -1
        else:
            self._recent_vertical_motion_sign = 0

        settings_controller.sync_first_person_target(self)
        self._first_person_motion.update(float(dt))
        self._hud_ctl.on_sim_step(dt=float(dt), player=self._session.player, jump_started=bool(step_result.jump_started))

        for break_event in tuple(step_result.gravity_broken_blocks):
            interaction_controller._spawn_break_particles(self, block_state=str(break_event.state_str), position=tuple(int(value) for value in break_event.cell))
            self._audio.play_interaction(action="break", block_state=str(break_event.state_str), position=tuple(int(value) for value in break_event.cell))

        if bool(step_result.footstep_triggered):
            self._audio.play_surface_event(event_name=PLAYER_EVENT_STEP, support_block_state=step_result.support_block_state, position=step_result.support_position)

        if bool(step_result.landed):
            self._audio.play_surface_event(event_name=PLAYER_EVENT_LAND, support_block_state=step_result.support_block_state, position=step_result.support_position, fall_distance_blocks=float(step_result.fall_distance_blocks))

        if self._state.is_othello_space():
            state_before = self._othello_match.game_state()
            state_after = self._othello_match.tick(float(dt), paused=False)
            if self._othello_state_changed(state_before, state_after):
                othello_controller.sync_hud_text(self)
                othello_controller.maybe_request_ai(self)
                othello_controller.maybe_request_analysis(self)
            else:
                now = time.perf_counter()
                if (float(now) - float(self._othello_last_passive_hud_sync_s)) >= 0.20:
                    self._othello_last_passive_hud_sync_s = float(now)
                    othello_controller.sync_hud_text(self)

        if float(self._session.player.position.y) < -64.0:
            self._set_dead_overlay(True)
            return

        interaction_controller.handle_held_mouse_buttons(self)
        self._emit_debug_hud_payload()
