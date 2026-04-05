# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

from ludoxel.application.runtime.ai_player_types import AI_MODE_IDLE, AI_MODE_ROUTE, AiRoutePoint, AiSpawnEggSettings
from ludoxel.application.runtime.state.ai_route_hotbar_defaults import default_ai_route_hotbar_slots
from ludoxel.shared.math.scalars import clampf
from ludoxel.shared.math.vec3 import Vec3
from ludoxel.shared.math.voxel.voxel_faces import FACE_POS_Y
from ludoxel.shared.systems.interaction_service import InteractionOutcome
from ludoxel.shared.ui.common.themed_notice_dialog import show_themed_notice
from ludoxel.shared.ui.hud.route_overlay_widget import RouteOverlayPath
from ludoxel.shared.ui.overlays.ai_settings_overlay import AiSettingsOverlay
from ludoxel.shared.world.inventory.hotbar import HOTBAR_SIZE
from ludoxel.shared.world.inventory.core_special_items import AI_ROUTE_CANCEL_ITEM_ID, AI_ROUTE_CONFIRM_ITEM_ID, AI_ROUTE_ERASE_ITEM_ID, AI_SPAWN_EGG_ITEM_ID

import ludoxel.shared.ui.viewport.controllers.settings_controller as settings_controller

if TYPE_CHECKING:
    from ludoxel.shared.ui.viewport.gl_viewport_widget import GLViewportWidget


def _ensure_edit_settings(viewport: "GLViewportWidget") -> None:
    viewport._ai_edit_settings = viewport._ai_edit_settings.normalized()


def route_edit_active(viewport: "GLViewportWidget") -> bool:
    return bool(viewport._state.route_edit_active)


def _eraser_selected(viewport: "GLViewportWidget") -> bool:
    item_id = settings_controller.current_item_id(viewport)
    return str(item_id) == AI_ROUTE_ERASE_ITEM_ID


def _hovered_route_point_index(viewport: "GLViewportWidget") -> int | None:
    if not bool(route_edit_active(viewport)) or (not bool(_eraser_selected(viewport))):
        return None
    if len(viewport._ai_route_edit_points) <= 0:
        return None

    eye, _yaw_deg, _pitch_deg, direction = viewport._interaction_pose()
    ray_direction = direction.normalized()
    if float(ray_direction.length()) <= 1e-6:
        return None
    world_hit = viewport._session.pick_block(reach=float(viewport._state.reach), origin=eye, direction=ray_direction)
    reach_limit = float(viewport._state.reach) if world_hit is None else min(float(viewport._state.reach), float(world_hit.t) + 0.05)

    best_index: int | None = None
    best_distance = 1e9
    for index, route_point in enumerate(viewport._ai_route_edit_points):
        point = route_point.as_vec3()
        delta = point - eye
        along = float(delta.dot(ray_direction))
        if float(along) < 0.0 or float(along) > float(reach_limit):
            continue
        nearest = eye + ray_direction * float(along)
        radial = float((point - nearest).length())
        if float(radial) > 0.32:
            continue
        if float(along) < float(best_distance):
            best_distance = float(along)
            best_index = int(index)
    return best_index


def route_overlay_paths(viewport: "GLViewportWidget") -> tuple[RouteOverlayPath, ...]:
    viewport._ai_route_hover_index = _hovered_route_point_index(viewport)
    paths: list[RouteOverlayPath] = []
    for route_path in viewport._session.ai_route_paths():
        points = tuple(point.as_vec3() for point in route_path.points)
        if len(points) >= 2:
            paths.append(RouteOverlayPath(points=points, closed=bool(route_path.closed), draft=False))
    if bool(route_edit_active(viewport)) and len(viewport._ai_route_edit_points) >= 1:
        points = tuple(point.as_vec3() for point in viewport._ai_route_edit_points)
        paths.append(RouteOverlayPath(points=points, closed=bool(viewport._ai_route_edit_closed), draft=True, highlighted_index=viewport._ai_route_hover_index))
    return tuple(paths)


def _sync_ai_visuals(viewport: "GLViewportWidget") -> None:
    viewport._sync_gameplay_hud_visibility()
    viewport._route_overlay.update()
    viewport.update()


def _spawn_ai_at_hit(viewport: "GLViewportWidget", *, hit) -> bool:
    if hit is None or hit.place is None:
        return False
    actor_id = viewport._session.spawn_ai_player(spawn_cell=tuple(int(value) for value in hit.place), settings=AiSpawnEggSettings(mode=AI_MODE_IDLE).normalized())
    if actor_id is None:
        return False
    _sync_ai_visuals(viewport)
    return True


def _open_actor_dialog(viewport: "GLViewportWidget", *, actor_id: str, initial_settings: AiSpawnEggSettings | None=None) -> bool:
    settings = None if initial_settings is None else initial_settings.normalized()
    if settings is None:
        settings = viewport._session.ai_player_settings(str(actor_id))
        if settings is None:
            return False
    viewport._ai_edit_actor_id = str(actor_id)
    viewport._ai_edit_settings = settings.normalized()
    _ensure_edit_settings(viewport)

    was_captured = bool(viewport._inp.captured())
    viewport._reset_held_mouse_actions()
    viewport._inp.reset()
    viewport._recent_move_f = 0.0
    viewport._recent_move_s = 0.0
    viewport._recent_jump_held = False
    viewport._recent_jump_pressed = False
    viewport._recent_crouch_held = False
    viewport._ai_settings_overlay_open = True
    viewport._inp.set_mouse_capture(False)
    settings_controller.sync_cloud_motion_pause(viewport)
    try:
        dialog = AiSettingsOverlay(parent=viewport.window() if viewport.window() is not None else viewport, settings=viewport._ai_edit_settings)
        viewport._position_detached_overlay_window(dialog)
        accepted = dialog.exec() == int(AiSettingsOverlay.DialogCode.Accepted)
        if not bool(accepted):
            return False
        if bool(dialog.delete_requested()):
            removed = viewport._session.remove_ai_player(str(actor_id))
            if bool(removed):
                _sync_ai_visuals(viewport)
            return bool(removed)
        viewport._ai_edit_settings = dialog.settings()
        if bool(dialog.route_edit_requested()):
            begin_route_edit(viewport, actor_id=str(actor_id), settings=viewport._ai_edit_settings)
            return True
        updated = viewport._session.update_ai_player_settings(actor_id=str(actor_id), settings=viewport._ai_edit_settings)
        if bool(updated):
            _sync_ai_visuals(viewport)
        return bool(updated)
    finally:
        viewport._ai_settings_overlay_open = False
        viewport._inp.reset()
        if not bool(route_edit_active(viewport)):
            viewport._ai_edit_actor_id = None
        settings_controller.sync_cloud_motion_pause(viewport)
        if bool(was_captured) and not viewport._overlays.any_modal_open() and not bool(viewport.loading_active()):
            viewport._inp.set_mouse_capture(True)
            viewport.arm_resume_refresh()


def begin_route_edit(viewport: "GLViewportWidget", *, actor_id: str, settings: AiSpawnEggSettings | None=None) -> None:
    resolved_settings = None if settings is None else settings.normalized()
    if resolved_settings is None:
        resolved_settings = viewport._session.ai_player_settings(str(actor_id))
    if resolved_settings is None:
        return
    viewport._session.cancel_ai_navigation(str(actor_id))
    viewport._ai_edit_actor_id = str(actor_id)
    viewport._ai_route_edit_actor_id = str(actor_id)
    viewport._ai_edit_settings = resolved_settings.normalized()
    _ensure_edit_settings(viewport)
    viewport._state.route_hotbar_slots = list(default_ai_route_hotbar_slots(size=HOTBAR_SIZE))
    viewport._state.route_selected_hotbar_index = 0
    viewport._state.route_edit_active = True
    viewport._state.normalize()
    viewport._ai_route_edit_points = list(viewport._ai_edit_settings.route_points)
    viewport._ai_route_edit_closed = bool(viewport._ai_edit_settings.route_closed)
    viewport._ai_route_hover_index = None
    settings_controller.sync_hotbar_widgets(viewport)
    settings_controller.sync_first_person_target(viewport)
    _sync_ai_visuals(viewport)


def _finish_route_edit(viewport: "GLViewportWidget", *, commit: bool, reopen_dialog: bool) -> None:
    actor_id = None if viewport._ai_route_edit_actor_id is None else str(viewport._ai_route_edit_actor_id)
    reopen_settings = viewport._ai_edit_settings.normalized()
    if bool(commit):
        if len(viewport._ai_route_edit_points) < 2:
            show_themed_notice(parent=viewport, title="AI Route", message="At least two route points are required.", nav_label="AI Route")
            return
        _ensure_edit_settings(viewport)
        viewport._ai_edit_settings = AiSpawnEggSettings(mode=AI_MODE_ROUTE, personality=viewport._ai_edit_settings.personality, can_place_blocks=bool(viewport._ai_edit_settings.can_place_blocks), route_points=tuple(viewport._ai_route_edit_points), route_closed=bool(viewport._ai_route_edit_closed), route_run=bool(viewport._ai_edit_settings.route_run), route_style=str(viewport._ai_edit_settings.route_style)).normalized()
        reopen_settings = viewport._ai_edit_settings.normalized()
        if actor_id is None or (not bool(viewport._session.update_ai_player_settings(actor_id=str(actor_id), settings=viewport._ai_edit_settings))):
            show_themed_notice(parent=viewport, title="AI Route", message="The selected AI is no longer available.", nav_label="AI Route")
            commit = False
            reopen_dialog = False
    viewport._state.route_edit_active = False
    viewport._state.normalize()
    viewport._ai_route_edit_points = []
    viewport._ai_route_edit_closed = False
    viewport._ai_route_hover_index = None
    viewport._ai_route_edit_actor_id = None
    settings_controller.sync_hotbar_widgets(viewport)
    settings_controller.sync_first_person_target(viewport)
    _sync_ai_visuals(viewport)
    if bool(reopen_dialog) and actor_id is not None:
        _open_actor_dialog(viewport, actor_id=str(actor_id), initial_settings=reopen_settings)
    else:
        viewport._ai_edit_actor_id = None


def cancel_route_edit(viewport: "GLViewportWidget", *, reopen_dialog: bool=False) -> None:
    if not bool(route_edit_active(viewport)):
        return
    _finish_route_edit(viewport, commit=False, reopen_dialog=bool(reopen_dialog))


def _route_point_from_top_face_hit(hit) -> AiRoutePoint | None:
    if hit is None or int(hit.face) != int(FACE_POS_Y):
        return None
    cell_x, _cell_y, cell_z = (int(hit.hit[0]), int(hit.hit[1]), int(hit.hit[2]))
    return AiRoutePoint(x=clampf(float(hit.hit_point.x), float(cell_x) + 0.15, float(cell_x) + 0.85), y=float(hit.hit_point.y), z=clampf(float(hit.hit_point.z), float(cell_z) + 0.15, float(cell_z) + 0.85))


def handle_route_left_click(viewport: "GLViewportWidget") -> bool:
    if not bool(route_edit_active(viewport)):
        return False

    viewport._first_person_motion.trigger_left_swing()
    if bool(_eraser_selected(viewport)):
        hover_index = _hovered_route_point_index(viewport)
        viewport._ai_route_hover_index = hover_index
        if hover_index is None:
            return True
        viewport._ai_route_edit_points.pop(int(hover_index))
        if len(viewport._ai_route_edit_points) < 3:
            viewport._ai_route_edit_closed = False
        viewport._route_overlay.update()
        return True

    interaction_eye, _yaw_deg, _pitch_deg, interaction_direction = viewport._interaction_pose()
    hit = viewport._session.pick_block(reach=float(viewport._state.reach), origin=interaction_eye, direction=interaction_direction)
    point = _route_point_from_top_face_hit(hit)
    if point is None:
        return True
    if len(viewport._ai_route_edit_points) >= 3:
        first = viewport._ai_route_edit_points[0]
        dx = float(point.x) - float(first.x)
        dz = float(point.z) - float(first.z)
        if (dx * dx + dz * dz) <= (0.90 * 0.90):
            viewport._ai_route_edit_closed = True
            viewport._route_overlay.update()
            return True
    viewport._ai_route_edit_closed = False
    viewport._ai_route_edit_points.append(point)
    viewport._route_overlay.update()
    return True


def _confirm_or_cancel_route_item(viewport: "GLViewportWidget", item_id: str) -> InteractionOutcome:
    reopen_dialog = viewport._ai_route_edit_actor_id is not None
    if str(item_id) == AI_ROUTE_CONFIRM_ITEM_ID:
        _finish_route_edit(viewport, commit=True, reopen_dialog=bool(reopen_dialog))
        return InteractionOutcome(success=not bool(route_edit_active(viewport)))
    if str(item_id) == AI_ROUTE_CANCEL_ITEM_ID:
        _finish_route_edit(viewport, commit=False, reopen_dialog=bool(reopen_dialog))
        return InteractionOutcome(success=True)
    return InteractionOutcome(success=False)


def handle_special_right_click(viewport: "GLViewportWidget", *, origin: Vec3, direction: Vec3, hit) -> InteractionOutcome | None:
    item_id = settings_controller.current_item_id(viewport)
    if bool(route_edit_active(viewport)):
        if str(item_id) in (AI_ROUTE_CONFIRM_ITEM_ID, AI_ROUTE_CANCEL_ITEM_ID):
            return _confirm_or_cancel_route_item(viewport, str(item_id))
        return InteractionOutcome(success=False)
    if str(item_id) == AI_SPAWN_EGG_ITEM_ID and hit is not None and hit.place is not None:
        return InteractionOutcome(success=bool(_spawn_ai_at_hit(viewport, hit=hit)))
    actor_id = viewport._session.pick_ai_player(origin=origin, direction=direction, reach=float(viewport._state.reach), block_hit=hit)
    if actor_id is not None:
        if not bool(viewport._state.creative_mode):
            return InteractionOutcome(success=False)
        return InteractionOutcome(success=bool(_open_actor_dialog(viewport, actor_id=str(actor_id))))
    return None


def extra_player_render_states(viewport: "GLViewportWidget", *, snapshot) -> tuple:
    del snapshot
    return tuple(viewport._session.ai_render_states())
