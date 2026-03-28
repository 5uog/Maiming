# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from pathlib import Path

from ....shared.blocks.models.api import collision_aabbs_for_block
from ....shared.blocks.state.state_codec import parse_state
from ....shared.blocks.state.state_values import prop_as_bool
from ....shared.blocks.structure.structural_rules import is_fence_gate
from ....shared.math.vec3 import Vec3
from ....shared.systems.gravity_system import GRAVITY_AFFECTED_TAG
from ....features.othello.domain.game.board import OTHELLO_BOARD_SURFACE_Y, ensure_othello_board_layout, is_othello_board_footprint
from ....features.othello.domain.game.types import OthelloGameState
from ....shared.world.play_space import normalize_play_space_id
from ..persistence import AppState, AppStateStore, PersistedOthelloSpace, PersistedPlaySpace, PersistedPlayer, PersistedWorld
from ..context.play_space_context import PlaySpaceContext
from ..state.runtime_preferences import RuntimePreferences, coerce_runtime_preferences
from ..managers.session_manager import SessionManager
from ..pipelines.runtime_state_pipeline import apply_persisted_settings_to_session, apply_runtime_to_renderer, persisted_inventory_from_runtime, persisted_settings_from_runtime, runtime_preferences_from_app_state


def _load_player_into_session(*, session: SessionManager, player: PersistedPlayer, allow_flying: bool) -> None:
    runtime_player = session.player
    runtime_player.position = Vec3(float(player.pos_x), float(player.pos_y), float(player.pos_z))
    runtime_player.velocity = Vec3(float(player.vel_x), float(player.vel_y), float(player.vel_z))
    runtime_player.yaw_deg = float(player.yaw_deg)
    runtime_player.pitch_deg = float(player.pitch_deg)
    runtime_player.clamp_pitch()
    runtime_player.on_ground = bool(player.on_ground)
    runtime_player.flying = bool(getattr(player, "flying", False)) and bool(allow_flying)
    runtime_player.crouch_eye_offset = float(max(0.0, min(float(runtime_player.crouch_eye_drop), float(player.crouch_eye_offset))))
    runtime_player.hold_jump_queued = False
    runtime_player.auto_jump_pending = False
    runtime_player.auto_jump_cooldown_s = float(max(0.0, float(player.auto_jump_cooldown_s)))
    runtime_player.auto_jump_start_y = float(runtime_player.position.y)
    runtime_player.fence_gate_overlap_exemption = None
    runtime_player.gravity_block_overlap_exemptions = ()


def _maybe_replace_world(session: SessionManager, persisted_world: PersistedWorld) -> None:
    if not persisted_world.blocks and int(persisted_world.revision) <= 0:
        return
    session.world.replace_all(blocks={key: str(value) for (key, value) in persisted_world.blocks.items()}, revision=int(max(1, int(persisted_world.revision))))


def _lift_player_above_othello_board_if_needed(session: SessionManager) -> None:
    player = session.player
    if not is_othello_board_footprint(float(player.position.x), float(player.position.z)):
        return
    board_surface_y = float(OTHELLO_BOARD_SURFACE_Y)
    if float(player.position.y) >= float(board_surface_y) - 1e-6:
        return
    player.position = Vec3(float(player.position.x), float(board_surface_y), float(player.position.z))
    player.velocity = Vec3(float(player.velocity.x), max(0.0, float(player.velocity.y)), float(player.velocity.z))
    player.on_ground = False
    player.auto_jump_start_y = float(player.position.y)


def _restore_player_overlap_exemptions(session: SessionManager) -> None:
    player = session.player
    world = session.world
    player_aabb = player.aabb_at(player.position)
    x0 = int(math.floor(float(player_aabb.mn.x))) - 1
    x1 = int(math.ceil(float(player_aabb.mx.x))) + 1
    y0 = int(math.floor(float(player_aabb.mn.y))) - 1
    y1 = int(math.ceil(float(player_aabb.mx.y))) + 1
    z0 = int(math.floor(float(player_aabb.mn.z))) - 1
    z1 = int(math.ceil(float(player_aabb.mx.z))) + 1

    fence_gate_cells: list[tuple[int, int, int]] = []
    gravity_cells: set[tuple[int, int, int]] = set()

    def get_state(x: int, y: int, z: int) -> str | None:
        return world.blocks.get((int(x), int(y), int(z)))

    for x in range(int(x0), int(x1) + 1):
        for y in range(int(y0), int(y1) + 1):
            for z in range(int(z0), int(z1) + 1):
                state_str = world.blocks.get((int(x), int(y), int(z)))
                if state_str is None:
                    continue
                base_id, props = parse_state(str(state_str))
                block_def = session.block_registry.get(str(base_id))
                if block_def is None:
                    continue

                closed_fence_gate = bool(is_fence_gate(block_def) and (not prop_as_bool(props, "open", False)))
                gravity_affected = bool(block_def.has_tag(GRAVITY_AFFECTED_TAG))
                if (not bool(closed_fence_gate)) and (not bool(gravity_affected)):
                    continue

                intersects = False
                for aabb in collision_aabbs_for_block(str(state_str), get_state, session.block_registry.get, int(x), int(y), int(z)):
                    if player_aabb.intersects(aabb):
                        intersects = True
                        break
                if not bool(intersects):
                    continue

                if bool(closed_fence_gate):
                    fence_gate_cells.append((int(x), int(y), int(z)))
                if bool(gravity_affected):
                    gravity_cells.add((int(x), int(y), int(z)))

    player.fence_gate_overlap_exemption = None if not fence_gate_cells else tuple(sorted(fence_gate_cells))[0]
    player.gravity_block_overlap_exemptions = tuple(sorted(gravity_cells))


def _persisted_player_from_session(session: SessionManager, *, allow_flying: bool) -> PersistedPlayer:
    player = session.player
    return PersistedPlayer(pos_x=float(player.position.x), pos_y=float(player.position.y), pos_z=float(player.position.z), vel_x=float(player.velocity.x), vel_y=float(player.velocity.y), vel_z=float(player.velocity.z), yaw_deg=float(player.yaw_deg), pitch_deg=float(player.pitch_deg), on_ground=bool(player.on_ground), flying=bool(player.flying and allow_flying), auto_jump_cooldown_s=float(max(0.0, float(player.auto_jump_cooldown_s))), crouch_eye_offset=float(max(0.0, min(float(player.crouch_eye_drop), float(player.crouch_eye_offset)))))


def _persisted_world_from_session(session: SessionManager) -> PersistedWorld:
    snapshot = session.snapshot_world_blocks_for_persistence()
    return PersistedWorld(revision=int(session.world.revision), blocks={key: str(value) for (key, value) in snapshot.items()})


def apply_persisted_state_if_present(*, project_root: Path, sessions: PlaySpaceContext, renderer) -> tuple[RuntimePreferences, OthelloGameState]:
    runtime = RuntimePreferences()
    store = AppStateStore(project_root=Path(project_root))
    state = store.load()
    othello_game_state = OthelloGameState()

    if state is not None:
        persisted_settings = state.settings
        for session in sessions.all_sessions():
            apply_persisted_settings_to_session(session, persisted_settings)

        runtime = runtime_preferences_from_app_state(state, runtime=runtime)

        _load_player_into_session(session=sessions.my_world, player=state.my_world.player, allow_flying=bool(runtime.creative_mode))
        _maybe_replace_world(sessions.my_world, state.my_world.world)
        _restore_player_overlap_exemptions(sessions.my_world)

        _load_player_into_session(session=sessions.othello, player=state.othello_space.player, allow_flying=False)
        _maybe_replace_world(sessions.othello, state.othello_space.world)
        ensure_othello_board_layout(sessions.othello.world)
        _lift_player_above_othello_board_if_needed(sessions.othello)
        _restore_player_overlap_exemptions(sessions.othello)
        othello_game_state = state.othello_space.othello_game_state.normalized()

    runtime.normalize()
    sessions.set_active_space(runtime.current_space_id)
    apply_runtime_to_renderer(runtime, renderer)
    return (runtime, othello_game_state)


def save_state(*, project_root: Path, sessions: PlaySpaceContext, renderer, runtime: RuntimePreferences | None=None, othello_game_state: OthelloGameState | None=None, **overrides) -> None:
    _ = renderer
    state_runtime = coerce_runtime_preferences(runtime=runtime, **overrides)
    store = AppStateStore(project_root=Path(project_root))
    active_session = sessions.active_session()

    settings = persisted_settings_from_runtime(state_runtime, active_session.settings)
    inventory = persisted_inventory_from_runtime(state_runtime)
    persisted_othello_state = (othello_game_state or OthelloGameState()).normalized()

    state = AppState(current_space_id=normalize_play_space_id(state_runtime.current_space_id), settings=settings, inventory=inventory, othello_settings=state_runtime.othello_settings.normalized(), my_world=PersistedPlaySpace(player=_persisted_player_from_session(sessions.my_world, allow_flying=bool(state_runtime.creative_mode)), world=_persisted_world_from_session(sessions.my_world)), othello_space=PersistedOthelloSpace(player=_persisted_player_from_session(sessions.othello, allow_flying=False), world=_persisted_world_from_session(sessions.othello), othello_game_state=persisted_othello_state))
    store.save(state)
