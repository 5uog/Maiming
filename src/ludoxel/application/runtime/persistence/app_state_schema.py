# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..state.audio_preferences import AudioPreferences
from ..keybinds import KeybindSettings
from ..player_name import normalize_player_name
from ..state.camera_perspective import CAMERA_PERSPECTIVE_FIRST_PERSON, normalize_camera_perspective
from ..state.runtime_preferences import RuntimePreferences
from ....shared.rendering.player_skin import PLAYER_SKIN_KIND_ALEX, normalize_player_skin_kind
from ....shared.ui.hud.crosshair_art import CROSSHAIR_MODE_DEFAULT, EMPTY_CROSSHAIR_PIXELS, normalize_crosshair_mode, normalize_crosshair_pixels
from ....shared.world.config.render_distance import clamp_render_distance_chunks
from ....shared.world.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from ....shared.world.inventory.hotbar import HOTBAR_SIZE as DOMAIN_HOTBAR_SIZE, normalize_hotbar_index, normalize_hotbar_slots
from ....shared.world.inventory.hotbar_defaults import default_hotbar_slots
from ....features.othello.domain.inventory.hotbar_defaults import default_othello_hotbar_slots
from ....features.othello.domain.game.types import OthelloGameState, OthelloSettings
from ....shared.math.scalar_coercion import coerce_bool, coerce_float, coerce_int, mapping_bool, mapping_float, mapping_int, mapping_str
from ....shared.world.play_space import PLAY_SPACE_MY_WORLD, normalize_play_space_id
from ....shared.world.world_state import WorldState


def _inventory_branch_to_dict(*, slots: object, selected_index: object, size: int) -> tuple[list[str], int]:
    normalized_slots = normalize_hotbar_slots(slots, size=int(size))
    normalized_index = normalize_hotbar_index(coerce_int(selected_index, 0), size=int(size))
    return [str(value) for value in normalized_slots], int(normalized_index)


def _inventory_branch_from_dict(raw_slots: object, raw_index: object, *, size: int, default_slots: tuple[str, ...], default_index: int) -> tuple[tuple[str, ...], int]:
    normalized_slots = normalize_hotbar_slots(default_slots if raw_slots is None else raw_slots, size=int(size))
    normalized_index = normalize_hotbar_index(coerce_int(raw_index, default_index), size=int(size))
    return normalized_slots, int(normalized_index)


def _coerce_xyz_triplet(raw: object, *, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if not isinstance(raw,(list, tuple)) or len(raw) != 3:
        raw = default
    return (coerce_float(raw[0], default[0]), coerce_float(raw[1], default[1]), coerce_float(raw[2], default[2]))


@dataclass(frozen=True)
class PersistedSettings:
    fov_deg: float = 80.0
    mouse_sens_deg_per_px: float = 0.09

    invert_x: bool = False
    invert_y: bool = False

    outline_selection: bool = True

    cloud_wireframe: bool = False
    world_wireframe: bool = False
    shadow_enabled: bool = True

    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0

    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337
    cloud_flow_direction: str = "west_to_east"

    creative_mode: bool = False
    block_break_repeat_interval_s: float = float(RuntimePreferences.DEFAULT_BLOCK_BREAK_REPEAT_INTERVAL_S)
    block_place_repeat_interval_s: float = float(RuntimePreferences.DEFAULT_BLOCK_PLACE_REPEAT_INTERVAL_S)
    block_interact_repeat_interval_s: float = float(RuntimePreferences.DEFAULT_BLOCK_INTERACT_REPEAT_INTERVAL_S)
    block_break_particle_spawn_rate: float = float(RuntimePreferences.DEFAULT_BLOCK_BREAK_PARTICLE_SPAWN_RATE)
    block_break_particle_speed_scale: float = float(RuntimePreferences.DEFAULT_BLOCK_BREAK_PARTICLE_SPEED_SCALE)
    auto_jump_enabled: bool = False
    auto_sprint_enabled: bool = False
    hide_hud: bool = False
    hide_hand: bool = False
    player_name: str = ""
    crosshair_mode: str = CROSSHAIR_MODE_DEFAULT
    crosshair_pixels: tuple[str, ...] = field(default_factory=lambda: EMPTY_CROSSHAIR_PIXELS)
    player_skin_kind: str = PLAYER_SKIN_KIND_ALEX
    camera_perspective: str = CAMERA_PERSPECTIVE_FIRST_PERSON
    fullscreen: bool = False
    view_bobbing_enabled: bool = True
    camera_shake_enabled: bool = True
    view_bobbing_strength: float = 0.35
    camera_shake_strength: float = 0.20
    arm_rotation_limit_min_deg: float = float(RuntimePreferences.DEFAULT_ARM_ROTATION_LIMIT_MIN_DEG)
    arm_rotation_limit_max_deg: float = float(RuntimePreferences.DEFAULT_ARM_ROTATION_LIMIT_MAX_DEG)
    arm_swing_duration_s: float = float(RuntimePreferences.DEFAULT_ARM_SWING_DURATION_S)
    animated_textures_enabled: bool = True

    gravity: float = float(DEFAULT_MOVEMENT_PARAMS.gravity)
    walk_speed: float = float(DEFAULT_MOVEMENT_PARAMS.walk_speed)
    sprint_speed: float = float(DEFAULT_MOVEMENT_PARAMS.sprint_speed)
    jump_v0: float = float(DEFAULT_MOVEMENT_PARAMS.jump_v0)
    auto_jump_cooldown_s: float = float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s)
    fly_speed: float = float(DEFAULT_MOVEMENT_PARAMS.fly_speed)
    fly_ascend_speed: float = float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed)
    fly_descend_speed: float = float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed)

    render_distance_chunks: int = 6
    debug_shadow: bool = False
    vsync_on: bool = False

    hud_visible: bool = False
    window_left: int | None = None
    window_top: int | None = None
    window_width: int = 1280
    window_height: int = 720
    window_screen_name: str = ""
    keybinds: KeybindSettings = field(default_factory=KeybindSettings)
    audio: AudioPreferences = field(default_factory=AudioPreferences)

    def to_dict(self) -> dict[str, Any]:
        return {"fov_deg": float(self.fov_deg), "mouse_sens_deg_per_px": float(self.mouse_sens_deg_per_px), "invert_x": bool(self.invert_x), "invert_y": bool(self.invert_y), "outline_selection": bool(self.outline_selection), "cloud_wireframe": bool(self.cloud_wireframe), "world_wireframe": bool(self.world_wireframe), "shadow_enabled": bool(self.shadow_enabled), "sun_az_deg": float(self.sun_az_deg), "sun_el_deg": float(self.sun_el_deg), "cloud_enabled": bool(self.cloud_enabled), "cloud_density": int(self.cloud_density), "cloud_seed": int(self.cloud_seed), "cloud_flow_direction": str(self.cloud_flow_direction), "creative_mode": bool(self.creative_mode), "block_break_repeat_interval_s": float(self.block_break_repeat_interval_s), "block_place_repeat_interval_s": float(self.block_place_repeat_interval_s), "block_interact_repeat_interval_s": float(self.block_interact_repeat_interval_s), "block_break_particle_spawn_rate": float(self.block_break_particle_spawn_rate), "block_break_particle_speed_scale": float(self.block_break_particle_speed_scale), "auto_jump_enabled": bool(self.auto_jump_enabled), "auto_sprint_enabled": bool(self.auto_sprint_enabled), "hide_hud": bool(self.hide_hud), "hide_hand": bool(self.hide_hand), "player_name": normalize_player_name(self.player_name), "crosshair_mode": normalize_crosshair_mode(self.crosshair_mode), "crosshair_pixels": list(normalize_crosshair_pixels(self.crosshair_pixels)), "player_skin_kind": normalize_player_skin_kind(self.player_skin_kind), "camera_perspective": normalize_camera_perspective(self.camera_perspective), "fullscreen": bool(self.fullscreen), "view_bobbing_enabled": bool(self.view_bobbing_enabled), "camera_shake_enabled": bool(self.camera_shake_enabled), "view_bobbing_strength": float(self.view_bobbing_strength), "camera_shake_strength": float(self.camera_shake_strength), "arm_rotation_limit_min_deg": float(self.arm_rotation_limit_min_deg), "arm_rotation_limit_max_deg": float(self.arm_rotation_limit_max_deg), "arm_swing_duration_s": float(self.arm_swing_duration_s), "animated_textures_enabled": bool(self.animated_textures_enabled), "gravity": float(self.gravity), "walk_speed": float(self.walk_speed), "sprint_speed": float(self.sprint_speed), "jump_v0": float(self.jump_v0), "auto_jump_cooldown_s": float(self.auto_jump_cooldown_s), "fly_speed": float(self.fly_speed), "fly_ascend_speed": float(self.fly_ascend_speed), "fly_descend_speed": float(self.fly_descend_speed), "render_distance_chunks": int(self.render_distance_chunks), "debug_shadow": bool(self.debug_shadow), "vsync_on": bool(self.vsync_on), "hud_visible": bool(self.hud_visible), "window_left": self.window_left, "window_top": self.window_top, "window_width": int(self.window_width), "window_height": int(self.window_height), "window_screen_name": str(self.window_screen_name), "keybinds": self.keybinds.normalized().to_dict(), "audio": self.audio.normalized().to_dict()}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedSettings":
        rd = clamp_render_distance_chunks(mapping_int(d, "render_distance_chunks", 6))

        return PersistedSettings(fov_deg=mapping_float(d, "fov_deg", 80.0), mouse_sens_deg_per_px=mapping_float(d, "mouse_sens_deg_per_px", 0.09), invert_x=mapping_bool(d, "invert_x", False), invert_y=mapping_bool(d, "invert_y", False), outline_selection=mapping_bool(d, "outline_selection", True), cloud_wireframe=mapping_bool(d, "cloud_wireframe", mapping_bool(d, "cloud_wire", False)), world_wireframe=mapping_bool(d, "world_wireframe", mapping_bool(d, "world_wire", False)), shadow_enabled=mapping_bool(d, "shadow_enabled", True), sun_az_deg=mapping_float(d, "sun_az_deg", 45.0), sun_el_deg=mapping_float(d, "sun_el_deg", 60.0), cloud_enabled=mapping_bool(d, "cloud_enabled", True), cloud_density=mapping_int(d, "cloud_density", 1), cloud_seed=mapping_int(d, "cloud_seed", 1337), cloud_flow_direction=mapping_str(d, "cloud_flow_direction", "west_to_east"), creative_mode=mapping_bool(d, "creative_mode", mapping_bool(d, "build_mode", False)), block_break_repeat_interval_s=mapping_float(d, "block_break_repeat_interval_s", float(RuntimePreferences.DEFAULT_BLOCK_BREAK_REPEAT_INTERVAL_S)), block_place_repeat_interval_s=mapping_float(d, "block_place_repeat_interval_s", float(RuntimePreferences.DEFAULT_BLOCK_PLACE_REPEAT_INTERVAL_S)), block_interact_repeat_interval_s=mapping_float(d, "block_interact_repeat_interval_s", float(RuntimePreferences.DEFAULT_BLOCK_INTERACT_REPEAT_INTERVAL_S)), block_break_particle_spawn_rate=mapping_float(d, "block_break_particle_spawn_rate", float(RuntimePreferences.DEFAULT_BLOCK_BREAK_PARTICLE_SPAWN_RATE)), block_break_particle_speed_scale=mapping_float(d, "block_break_particle_speed_scale", float(RuntimePreferences.DEFAULT_BLOCK_BREAK_PARTICLE_SPEED_SCALE)), auto_jump_enabled=mapping_bool(d, "auto_jump_enabled", False), auto_sprint_enabled=mapping_bool(d, "auto_sprint_enabled", False), hide_hud=mapping_bool(d, "hide_hud", False), hide_hand=mapping_bool(d, "hide_hand", False), player_name=normalize_player_name(mapping_str(d, "player_name", "")), crosshair_mode=normalize_crosshair_mode(mapping_str(d, "crosshair_mode", CROSSHAIR_MODE_DEFAULT)), crosshair_pixels=normalize_crosshair_pixels(d.get("crosshair_pixels", EMPTY_CROSSHAIR_PIXELS)), player_skin_kind=normalize_player_skin_kind(mapping_str(d, "player_skin_kind", PLAYER_SKIN_KIND_ALEX)), camera_perspective=normalize_camera_perspective(mapping_str(d, "camera_perspective", CAMERA_PERSPECTIVE_FIRST_PERSON)), fullscreen=mapping_bool(d, "fullscreen", False), view_bobbing_enabled=mapping_bool(d, "view_bobbing_enabled", True), camera_shake_enabled=mapping_bool(d, "camera_shake_enabled", True), view_bobbing_strength=mapping_float(d, "view_bobbing_strength", 0.35), camera_shake_strength=mapping_float(d, "camera_shake_strength", 0.20), arm_rotation_limit_min_deg=mapping_float(d, "arm_rotation_limit_min_deg", float(RuntimePreferences.DEFAULT_ARM_ROTATION_LIMIT_MIN_DEG)), arm_rotation_limit_max_deg=mapping_float(d, "arm_rotation_limit_max_deg", float(RuntimePreferences.DEFAULT_ARM_ROTATION_LIMIT_MAX_DEG)), arm_swing_duration_s=mapping_float(d, "arm_swing_duration_s", float(RuntimePreferences.DEFAULT_ARM_SWING_DURATION_S)), animated_textures_enabled=mapping_bool(d, "animated_textures_enabled", True), gravity=mapping_float(d, "gravity", float(DEFAULT_MOVEMENT_PARAMS.gravity)), walk_speed=mapping_float(d, "walk_speed", float(DEFAULT_MOVEMENT_PARAMS.walk_speed)), sprint_speed=mapping_float(d, "sprint_speed", float(DEFAULT_MOVEMENT_PARAMS.sprint_speed)), jump_v0=mapping_float(d, "jump_v0", float(DEFAULT_MOVEMENT_PARAMS.jump_v0)), auto_jump_cooldown_s=mapping_float(d, "auto_jump_cooldown_s", float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s)), fly_speed=mapping_float(d, "fly_speed", float(DEFAULT_MOVEMENT_PARAMS.fly_speed)), fly_ascend_speed=mapping_float(d, "fly_ascend_speed", float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed)), fly_descend_speed=mapping_float(d, "fly_descend_speed", float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed)), render_distance_chunks=int(rd), debug_shadow=mapping_bool(d, "debug_shadow", False), vsync_on=mapping_bool(d, "vsync_on", False), hud_visible=mapping_bool(d, "hud_visible", False), window_left=(None if d.get("window_left") is None else coerce_int(d.get("window_left"), 0)), window_top=(None if d.get("window_top") is None else coerce_int(d.get("window_top"), 0)), window_width=max(320, coerce_int(d.get("window_width", 1280), 1280)), window_height=max(240, coerce_int(d.get("window_height", 720), 720)), window_screen_name=mapping_str(d, "window_screen_name", ""), keybinds=KeybindSettings.from_dict(d.get("keybinds",{})), audio=AudioPreferences.from_dict(d.get("audio",{})))


@dataclass(frozen=True)
class PersistedInventory:
    HOTBAR_SIZE: ClassVar[int] = DOMAIN_HOTBAR_SIZE

    creative_hotbar_slots: tuple[str, ...] = field(default_factory=lambda: default_hotbar_slots(size=DOMAIN_HOTBAR_SIZE))
    creative_selected_hotbar_index: int = 0
    survival_hotbar_slots: tuple[str, ...] = field(default_factory=lambda: default_hotbar_slots(size=DOMAIN_HOTBAR_SIZE))
    survival_selected_hotbar_index: int = 0
    othello_hotbar_slots: tuple[str, ...] = field(default_factory=lambda: default_othello_hotbar_slots(size=DOMAIN_HOTBAR_SIZE))
    othello_selected_hotbar_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        creative_slots, creative_idx = _inventory_branch_to_dict(slots=self.creative_hotbar_slots, selected_index=self.creative_selected_hotbar_index, size=self.HOTBAR_SIZE)
        survival_slots, survival_idx = _inventory_branch_to_dict(slots=self.survival_hotbar_slots, selected_index=self.survival_selected_hotbar_index, size=self.HOTBAR_SIZE)
        othello_slots, othello_idx = _inventory_branch_to_dict(slots=self.othello_hotbar_slots, selected_index=self.othello_selected_hotbar_index, size=self.HOTBAR_SIZE)

        return {"creative_hotbar_slots": creative_slots, "creative_selected_hotbar_index": int(creative_idx), "survival_hotbar_slots": survival_slots, "survival_selected_hotbar_index": int(survival_idx), "othello_hotbar_slots": othello_slots, "othello_selected_hotbar_index": int(othello_idx)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedInventory":
        legacy_slots, legacy_idx = _inventory_branch_from_dict(d.get("hotbar_slots"), d.get("selected_hotbar_index", 0), size=PersistedInventory.HOTBAR_SIZE, default_slots=default_hotbar_slots(size=PersistedInventory.HOTBAR_SIZE), default_index=0)
        creative_slots, creative_idx = _inventory_branch_from_dict(d.get("creative_hotbar_slots", legacy_slots), d.get("creative_selected_hotbar_index", legacy_idx), size=PersistedInventory.HOTBAR_SIZE, default_slots=legacy_slots, default_index=legacy_idx)
        survival_slots, survival_idx = _inventory_branch_from_dict(d.get("survival_hotbar_slots", legacy_slots), d.get("survival_selected_hotbar_index", legacy_idx), size=PersistedInventory.HOTBAR_SIZE, default_slots=legacy_slots, default_index=legacy_idx)
        othello_slots, othello_idx = _inventory_branch_from_dict(d.get("othello_hotbar_slots", default_othello_hotbar_slots(size=PersistedInventory.HOTBAR_SIZE)), d.get("othello_selected_hotbar_index", 0), size=PersistedInventory.HOTBAR_SIZE, default_slots=default_othello_hotbar_slots(size=PersistedInventory.HOTBAR_SIZE), default_index=0)

        return PersistedInventory(creative_hotbar_slots=creative_slots, creative_selected_hotbar_index=int(creative_idx), survival_hotbar_slots=survival_slots, survival_selected_hotbar_index=int(survival_idx), othello_hotbar_slots=othello_slots, othello_selected_hotbar_index=int(othello_idx))


@dataclass(frozen=True)
class PersistedPlayer:
    pos_x: float = 0.0
    pos_y: float = 1.0
    pos_z: float = -10.0

    vel_x: float = 0.0
    vel_y: float = 0.0
    vel_z: float = 0.0

    yaw_deg: float = 0.0
    pitch_deg: float = 0.0

    on_ground: bool = False
    flying: bool = False
    auto_jump_cooldown_s: float = 0.0
    crouch_eye_offset: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"pos": [float(self.pos_x), float(self.pos_y), float(self.pos_z)], "vel": [float(self.vel_x), float(self.vel_y), float(self.vel_z)], "yaw_deg": float(self.yaw_deg), "pitch_deg": float(self.pitch_deg), "on_ground": bool(self.on_ground), "flying": bool(self.flying), "auto_jump_cooldown_s": float(self.auto_jump_cooldown_s), "crouch_eye_offset": float(self.crouch_eye_offset)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedPlayer":
        pos_x, pos_y, pos_z = _coerce_xyz_triplet(d.get("pos"), default=(0.0, 1.0, -10.0))
        vel_x, vel_y, vel_z = _coerce_xyz_triplet(d.get("vel"), default=(0.0, 0.0, 0.0))

        cooldown_raw = d.get("auto_jump_cooldown_s", d.get("jump_cooldown_s", 0.0))

        return PersistedPlayer(pos_x=pos_x, pos_y=pos_y, pos_z=pos_z, vel_x=vel_x, vel_y=vel_y, vel_z=vel_z, yaw_deg=coerce_float(d.get("yaw_deg", 0.0), 0.0), pitch_deg=coerce_float(d.get("pitch_deg", 0.0), 0.0), on_ground=coerce_bool(d.get("on_ground", False), False), flying=coerce_bool(d.get("flying", False), False), auto_jump_cooldown_s=coerce_float(cooldown_raw, 0.0), crouch_eye_offset=coerce_float(d.get("crouch_eye_offset", 0.0), 0.0))


@dataclass(frozen=True)
class PersistedWorld:
    revision: int = 0
    blocks: dict[tuple[int, int, int], str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        world = WorldState(blocks=dict(self.blocks), revision=int(self.revision))
        return world.to_persisted_dict()

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedWorld":
        world = WorldState.from_persisted_dict(d)
        return PersistedWorld(revision=int(world.revision), blocks=world.snapshot_blocks())


@dataclass(frozen=True)
class PersistedPlaySpace:
    player: PersistedPlayer = field(default_factory=PersistedPlayer)
    world: PersistedWorld = field(default_factory=PersistedWorld)

    def to_dict(self) -> dict[str, Any]:
        return {"player": self.player.to_dict(), "world": self.world.to_dict()}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PersistedPlaySpace":
        if not isinstance(data, dict):
            return PersistedPlaySpace()

        raw_player = data.get("player",{})
        raw_world = data.get("world",{})
        return PersistedPlaySpace(player=PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer(), world=PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld())


@dataclass(frozen=True)
class PersistedOthelloSpace:
    player: PersistedPlayer = field(default_factory=PersistedPlayer)
    world: PersistedWorld = field(default_factory=PersistedWorld)
    othello_game_state: OthelloGameState = field(default_factory=OthelloGameState)

    def to_dict(self) -> dict[str, Any]:
        return {"player": self.player.to_dict(), "world": self.world.to_dict(), "othello_game_state": self.othello_game_state.to_dict()}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PersistedOthelloSpace":
        if not isinstance(data, dict):
            return PersistedOthelloSpace()

        raw_player = data.get("player",{})
        raw_world = data.get("world",{})
        raw_game = data.get("othello_game_state",{})
        return PersistedOthelloSpace(player=PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer(), world=PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld(), othello_game_state=(OthelloGameState.from_dict(raw_game) if isinstance(raw_game, dict) else OthelloGameState()))


@dataclass(frozen=True)
class PlayerStateFile:
    version: int = 6
    current_space_id: str = PLAY_SPACE_MY_WORLD
    settings: PersistedSettings = field(default_factory=PersistedSettings)
    inventory: PersistedInventory = field(default_factory=PersistedInventory)
    othello_settings: OthelloSettings = field(default_factory=OthelloSettings)

    def to_dict(self) -> dict[str, Any]:
        return {"version": int(self.version), "current_space_id": str(normalize_play_space_id(self.current_space_id)), "settings": self.settings.to_dict(), "inventory": self.inventory.to_dict(), "othello_settings": self.othello_settings.normalized().to_dict()}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PlayerStateFile":
        if not isinstance(d, dict):
            return PlayerStateFile()

        version = coerce_int(d.get("version", 1), 1)
        raw_settings = d.get("settings",{})
        raw_inventory = d.get("inventory",{})
        raw_othello_settings = d.get("othello_settings",{})

        settings = PersistedSettings.from_dict(raw_settings) if isinstance(raw_settings, dict) else PersistedSettings()
        inventory = PersistedInventory.from_dict(raw_inventory) if isinstance(raw_inventory, dict) else PersistedInventory()
        othello_settings = (OthelloSettings.from_dict(raw_othello_settings) if isinstance(raw_othello_settings, dict) else OthelloSettings())

        return PlayerStateFile(version=int(max(1, version)), current_space_id=normalize_play_space_id(d.get("current_space_id", PLAY_SPACE_MY_WORLD)), settings=settings, inventory=inventory, othello_settings=othello_settings)


@dataclass(frozen=True)
class WorldStateFile:
    version: int = 2
    my_world: PersistedPlaySpace = field(default_factory=PersistedPlaySpace)
    othello_space: PersistedOthelloSpace = field(default_factory=PersistedOthelloSpace)

    def to_dict(self) -> dict[str, Any]:
        return {"version": int(self.version), "spaces": {"my_world": self.my_world.to_dict(), "othello": self.othello_space.to_dict()}}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "WorldStateFile":
        if not isinstance(d, dict):
            return WorldStateFile()

        version = coerce_int(d.get("version", 1), 1)

        if "spaces" not in d:
            raw_player = d.get("player",{})
            raw_world = d.get("world",{})
            my_world = PersistedPlaySpace(player=PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer(), world=PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld())
            return WorldStateFile(version=int(max(2, version)), my_world=my_world, othello_space=PersistedOthelloSpace())

        raw_spaces = d.get("spaces",{})
        if not isinstance(raw_spaces, dict):
            raw_spaces = {}

        raw_my_world = raw_spaces.get("my_world",{})
        raw_othello = raw_spaces.get("othello",{})

        my_world = (PersistedPlaySpace.from_dict(raw_my_world) if isinstance(raw_my_world, dict) else PersistedPlaySpace())
        othello_space = (PersistedOthelloSpace.from_dict(raw_othello) if isinstance(raw_othello, dict) else PersistedOthelloSpace())

        return WorldStateFile(version=int(max(2, version)), my_world=my_world, othello_space=othello_space)


@dataclass(frozen=True)
class AppState:
    current_space_id: str
    settings: PersistedSettings
    inventory: PersistedInventory
    othello_settings: OthelloSettings
    my_world: PersistedPlaySpace
    othello_space: PersistedOthelloSpace

    @staticmethod
    def default() -> "AppState":
        return AppState(current_space_id=PLAY_SPACE_MY_WORLD, settings=PersistedSettings(), inventory=PersistedInventory(), othello_settings=OthelloSettings(), my_world=PersistedPlaySpace(), othello_space=PersistedOthelloSpace())
