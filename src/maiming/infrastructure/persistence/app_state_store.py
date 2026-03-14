# FILE: src/maiming/infrastructure/persistence/app_state_store.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, Tuple

from ...domain.config.render_distance import clamp_render_distance_chunks
from ...domain.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from ...domain.inventory.hotbar import HOTBAR_SIZE as DOMAIN_HOTBAR_SIZE, normalize_hotbar_index, normalize_hotbar_slots
from ...domain.inventory.special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID
from ...domain.othello.types import OthelloGameState, OthelloSettings
from ...domain.play_space import PLAY_SPACE_MY_WORLD, normalize_play_space_id
from ...domain.world.world_state import WorldState
from .json_file_store import JsonFileStore
from .scalar_coercion import coerce_bool, coerce_float, coerce_int, mapping_bool, mapping_float, mapping_int, mapping_str

def _default_othello_hotbar_slots() -> tuple[str, ...]:
    return normalize_hotbar_slots(
        (
            OTHELLO_START_ITEM_ID,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            OTHELLO_SETTINGS_ITEM_ID,
        ),
        size=DOMAIN_HOTBAR_SIZE,
    )

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
    auto_jump_enabled: bool = False
    auto_sprint_enabled: bool = False
    hide_hud: bool = False
    hide_hand: bool = False
    fullscreen: bool = False
    view_bobbing_enabled: bool = True
    camera_shake_enabled: bool = True
    view_bobbing_strength: float = 0.35
    camera_shake_strength: float = 0.20

    gravity: float = float(DEFAULT_MOVEMENT_PARAMS.gravity)
    walk_speed: float = float(DEFAULT_MOVEMENT_PARAMS.walk_speed)
    sprint_speed: float = float(DEFAULT_MOVEMENT_PARAMS.sprint_speed)
    jump_v0: float = float(DEFAULT_MOVEMENT_PARAMS.jump_v0)
    auto_jump_cooldown_s: float = float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s)
    fly_speed: float = float(DEFAULT_MOVEMENT_PARAMS.fly_speed)
    fly_ascend_speed: float = float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed)
    fly_descend_speed: float = float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed)

    render_distance_chunks: int = 6

    hud_visible: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "fov_deg": float(self.fov_deg),
            "mouse_sens_deg_per_px": float(self.mouse_sens_deg_per_px),
            "invert_x": bool(self.invert_x),
            "invert_y": bool(self.invert_y),
            "outline_selection": bool(self.outline_selection),
            "cloud_wireframe": bool(self.cloud_wireframe),
            "world_wireframe": bool(self.world_wireframe),
            "shadow_enabled": bool(self.shadow_enabled),
            "sun_az_deg": float(self.sun_az_deg),
            "sun_el_deg": float(self.sun_el_deg),
            "cloud_enabled": bool(self.cloud_enabled),
            "cloud_density": int(self.cloud_density),
            "cloud_seed": int(self.cloud_seed),
            "cloud_flow_direction": str(self.cloud_flow_direction),
            "creative_mode": bool(self.creative_mode),
            "auto_jump_enabled": bool(self.auto_jump_enabled),
            "auto_sprint_enabled": bool(self.auto_sprint_enabled),
            "hide_hud": bool(self.hide_hud),
            "hide_hand": bool(self.hide_hand),
            "fullscreen": bool(self.fullscreen),
            "view_bobbing_enabled": bool(self.view_bobbing_enabled),
            "camera_shake_enabled": bool(self.camera_shake_enabled),
            "view_bobbing_strength": float(self.view_bobbing_strength),
            "camera_shake_strength": float(self.camera_shake_strength),
            "gravity": float(self.gravity),
            "walk_speed": float(self.walk_speed),
            "sprint_speed": float(self.sprint_speed),
            "jump_v0": float(self.jump_v0),
            "auto_jump_cooldown_s": float(self.auto_jump_cooldown_s),
            "fly_speed": float(self.fly_speed),
            "fly_ascend_speed": float(self.fly_ascend_speed),
            "fly_descend_speed": float(self.fly_descend_speed),
            "render_distance_chunks": int(self.render_distance_chunks),
            "hud_visible": bool(self.hud_visible),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedSettings":
        rd = clamp_render_distance_chunks(mapping_int(d, "render_distance_chunks", 6))

        return PersistedSettings(
            fov_deg=mapping_float(d, "fov_deg", 80.0),
            mouse_sens_deg_per_px=mapping_float(d, "mouse_sens_deg_per_px", 0.09),
            invert_x=mapping_bool(d, "invert_x", False),
            invert_y=mapping_bool(d, "invert_y", False),
            outline_selection=mapping_bool(d, "outline_selection", True),
            cloud_wireframe=mapping_bool(d, "cloud_wireframe", mapping_bool(d, "cloud_wire", False)),
            world_wireframe=mapping_bool(d, "world_wireframe", False),
            shadow_enabled=mapping_bool(d, "shadow_enabled", True),
            sun_az_deg=mapping_float(d, "sun_az_deg", 45.0),
            sun_el_deg=mapping_float(d, "sun_el_deg", 60.0),
            cloud_enabled=mapping_bool(d, "cloud_enabled", True),
            cloud_density=mapping_int(d, "cloud_density", 1),
            cloud_seed=mapping_int(d, "cloud_seed", 1337),
            cloud_flow_direction=mapping_str(d, "cloud_flow_direction", "west_to_east"),
            creative_mode=mapping_bool(d, "creative_mode", mapping_bool(d, "build_mode", False)),
            auto_jump_enabled=mapping_bool(d, "auto_jump_enabled", False),
            auto_sprint_enabled=mapping_bool(d, "auto_sprint_enabled", False),
            hide_hud=mapping_bool(d, "hide_hud", False),
            hide_hand=mapping_bool(d, "hide_hand", False),
            fullscreen=mapping_bool(d, "fullscreen", False),
            view_bobbing_enabled=mapping_bool(d, "view_bobbing_enabled", True),
            camera_shake_enabled=mapping_bool(d, "camera_shake_enabled", True),
            view_bobbing_strength=mapping_float(d, "view_bobbing_strength", 0.35),
            camera_shake_strength=mapping_float(d, "camera_shake_strength", 0.20),
            gravity=mapping_float(d, "gravity", float(DEFAULT_MOVEMENT_PARAMS.gravity)),
            walk_speed=mapping_float(d, "walk_speed", float(DEFAULT_MOVEMENT_PARAMS.walk_speed)),
            sprint_speed=mapping_float(d, "sprint_speed", float(DEFAULT_MOVEMENT_PARAMS.sprint_speed)),
            jump_v0=mapping_float(d, "jump_v0", float(DEFAULT_MOVEMENT_PARAMS.jump_v0)),
            auto_jump_cooldown_s=mapping_float(d, "auto_jump_cooldown_s", float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s)),
            fly_speed=mapping_float(d, "fly_speed", float(DEFAULT_MOVEMENT_PARAMS.fly_speed)),
            fly_ascend_speed=mapping_float(d, "fly_ascend_speed", float(DEFAULT_MOVEMENT_PARAMS.fly_ascend_speed)),
            fly_descend_speed=mapping_float(d, "fly_descend_speed", float(DEFAULT_MOVEMENT_PARAMS.fly_descend_speed)),
            render_distance_chunks=int(rd),
            hud_visible=mapping_bool(d, "hud_visible", False),
        )

@dataclass(frozen=True)
class PersistedInventory:
    HOTBAR_SIZE: ClassVar[int] = DOMAIN_HOTBAR_SIZE

    creative_hotbar_slots: tuple[str, ...] = ("", "", "", "", "", "", "", "", "")
    creative_selected_hotbar_index: int = 0
    survival_hotbar_slots: tuple[str, ...] = ("", "", "", "", "", "", "", "", "")
    survival_selected_hotbar_index: int = 0
    othello_hotbar_slots: tuple[str, ...] = _default_othello_hotbar_slots()
    othello_selected_hotbar_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        creative_slots = normalize_hotbar_slots(self.creative_hotbar_slots, size=self.HOTBAR_SIZE)
        creative_idx = normalize_hotbar_index(self.creative_selected_hotbar_index, size=self.HOTBAR_SIZE)
        survival_slots = normalize_hotbar_slots(self.survival_hotbar_slots, size=self.HOTBAR_SIZE)
        survival_idx = normalize_hotbar_index(self.survival_selected_hotbar_index, size=self.HOTBAR_SIZE)
        othello_slots = normalize_hotbar_slots(self.othello_hotbar_slots, size=self.HOTBAR_SIZE)
        othello_idx = normalize_hotbar_index(self.othello_selected_hotbar_index, size=self.HOTBAR_SIZE)

        return {
            "creative_hotbar_slots": [str(v) for v in creative_slots],
            "creative_selected_hotbar_index": int(creative_idx),
            "survival_hotbar_slots": [str(v) for v in survival_slots],
            "survival_selected_hotbar_index": int(survival_idx),
            "othello_hotbar_slots": [str(v) for v in othello_slots],
            "othello_selected_hotbar_index": int(othello_idx),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedInventory":
        legacy_slots = normalize_hotbar_slots(d.get("hotbar_slots", []), size=PersistedInventory.HOTBAR_SIZE)
        legacy_idx = normalize_hotbar_index(coerce_int(d.get("selected_hotbar_index", 0), 0), size=PersistedInventory.HOTBAR_SIZE)

        creative_slots = normalize_hotbar_slots(d.get("creative_hotbar_slots", legacy_slots), size=PersistedInventory.HOTBAR_SIZE)
        creative_idx = normalize_hotbar_index(coerce_int(d.get("creative_selected_hotbar_index", legacy_idx), legacy_idx), size=PersistedInventory.HOTBAR_SIZE)

        survival_slots = normalize_hotbar_slots(d.get("survival_hotbar_slots", legacy_slots), size=PersistedInventory.HOTBAR_SIZE)
        survival_idx = normalize_hotbar_index(coerce_int(d.get("survival_selected_hotbar_index", legacy_idx), legacy_idx), size=PersistedInventory.HOTBAR_SIZE)

        othello_slots = normalize_hotbar_slots(d.get("othello_hotbar_slots", _default_othello_hotbar_slots()), size=PersistedInventory.HOTBAR_SIZE)
        othello_idx = normalize_hotbar_index(coerce_int(d.get("othello_selected_hotbar_index", 0), 0), size=PersistedInventory.HOTBAR_SIZE)

        return PersistedInventory(
            creative_hotbar_slots=creative_slots,
            creative_selected_hotbar_index=int(creative_idx),
            survival_hotbar_slots=survival_slots,
            survival_selected_hotbar_index=int(survival_idx),
            othello_hotbar_slots=othello_slots,
            othello_selected_hotbar_index=int(othello_idx),
        )

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
        return {
            "pos": [float(self.pos_x), float(self.pos_y), float(self.pos_z)],
            "vel": [float(self.vel_x), float(self.vel_y), float(self.vel_z)],
            "yaw_deg": float(self.yaw_deg),
            "pitch_deg": float(self.pitch_deg),
            "on_ground": bool(self.on_ground),
            "flying": bool(self.flying),
            "auto_jump_cooldown_s": float(self.auto_jump_cooldown_s),
            "crouch_eye_offset": float(self.crouch_eye_offset),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedPlayer":
        pos = d.get("pos", [0.0, 1.0, -10.0])
        vel = d.get("vel", [0.0, 0.0, 0.0])

        if not isinstance(pos, list) or len(pos) != 3:
            pos = [0.0, 1.0, -10.0]
        if not isinstance(vel, list) or len(vel) != 3:
            vel = [0.0, 0.0, 0.0]

        cooldown_raw = d.get("auto_jump_cooldown_s", d.get("jump_cooldown_s", 0.0))

        return PersistedPlayer(
            pos_x=coerce_float(pos[0], 0.0),
            pos_y=coerce_float(pos[1], 1.0),
            pos_z=coerce_float(pos[2], -10.0),
            vel_x=coerce_float(vel[0], 0.0),
            vel_y=coerce_float(vel[1], 0.0),
            vel_z=coerce_float(vel[2], 0.0),
            yaw_deg=coerce_float(d.get("yaw_deg", 0.0), 0.0),
            pitch_deg=coerce_float(d.get("pitch_deg", 0.0), 0.0),
            on_ground=coerce_bool(d.get("on_ground", False), False),
            flying=coerce_bool(d.get("flying", False), False),
            auto_jump_cooldown_s=coerce_float(cooldown_raw, 0.0),
            crouch_eye_offset=coerce_float(d.get("crouch_eye_offset", 0.0), 0.0),
        )

@dataclass(frozen=True)
class PersistedWorld:
    revision: int
    blocks: Dict[Tuple[int, int, int], str]

    def to_dict(self) -> dict[str, Any]:
        world = WorldState(blocks=dict(self.blocks), revision=int(self.revision))
        return world.to_persisted_dict()

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedWorld":
        world = WorldState.from_persisted_dict(d)
        return PersistedWorld(revision=int(world.revision), blocks=world.snapshot_blocks())

@dataclass(frozen=True)
class PersistedPlaySpace:
    player: PersistedPlayer = PersistedPlayer()
    world: PersistedWorld = PersistedWorld(revision=0, blocks={})

    def to_dict(self) -> dict[str, Any]:
        return {"player": self.player.to_dict(), "world": self.world.to_dict()}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PersistedPlaySpace":
        if not isinstance(data, dict):
            return PersistedPlaySpace()
        raw_player = data.get("player", {})
        raw_world = data.get("world", {})
        return PersistedPlaySpace(player=PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer(), world=PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld(revision=0, blocks={}))

@dataclass(frozen=True)
class PersistedOthelloSpace:
    player: PersistedPlayer = PersistedPlayer()
    world: PersistedWorld = PersistedWorld(revision=0, blocks={})
    othello_game_state: OthelloGameState = OthelloGameState()

    def to_dict(self) -> dict[str, Any]:
        return {"player": self.player.to_dict(), "world": self.world.to_dict(), "othello_game_state": self.othello_game_state.to_dict()}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PersistedOthelloSpace":
        if not isinstance(data, dict):
            return PersistedOthelloSpace()
        raw_player = data.get("player", {})
        raw_world = data.get("world", {})
        raw_game = data.get("othello_game_state", {})
        return PersistedOthelloSpace(player=PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer(), world=PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld(revision=0, blocks={}), othello_game_state=OthelloGameState.from_dict(raw_game) if isinstance(raw_game, dict) else OthelloGameState())

@dataclass(frozen=True)
class PlayerStateFile:
    version: int = 2
    current_space_id: str = PLAY_SPACE_MY_WORLD
    settings: PersistedSettings = PersistedSettings()
    inventory: PersistedInventory = PersistedInventory()
    othello_settings: OthelloSettings = OthelloSettings()

    def to_dict(self) -> dict[str, Any]:
        return {"version": int(self.version), "current_space_id": str(normalize_play_space_id(self.current_space_id)), "settings": self.settings.to_dict(), "inventory": self.inventory.to_dict(), "othello_settings": self.othello_settings.normalized().to_dict()}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PlayerStateFile":
        if not isinstance(d, dict):
            return PlayerStateFile()

        version = coerce_int(d.get("version", 1), 1)
        raw_settings = d.get("settings", {})
        raw_inventory = d.get("inventory", {})
        raw_othello_settings = d.get("othello_settings", {})

        settings = PersistedSettings.from_dict(raw_settings) if isinstance(raw_settings, dict) else PersistedSettings()
        inventory = PersistedInventory.from_dict(raw_inventory) if isinstance(raw_inventory, dict) else PersistedInventory()
        othello_settings = OthelloSettings.from_dict(raw_othello_settings) if isinstance(raw_othello_settings, dict) else OthelloSettings()

        return PlayerStateFile(version=int(max(1, version)), current_space_id=normalize_play_space_id(d.get("current_space_id", PLAY_SPACE_MY_WORLD)), settings=settings, inventory=inventory, othello_settings=othello_settings)

@dataclass(frozen=True)
class WorldStateFile:
    version: int = 2
    my_world: PersistedPlaySpace = PersistedPlaySpace()
    othello_space: PersistedOthelloSpace = PersistedOthelloSpace()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": int(self.version),
            "spaces": {
                "my_world": self.my_world.to_dict(),
                "othello": self.othello_space.to_dict(),
            },
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "WorldStateFile":
        if not isinstance(d, dict):
            return WorldStateFile()

        version = coerce_int(d.get("version", 1), 1)

        if "spaces" not in d:
            raw_player = d.get("player", {})
            raw_world = d.get("world", {})
            my_world = PersistedPlaySpace(
                player=PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer(),
                world=PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld(revision=0, blocks={}),
            )
            return WorldStateFile(version=int(max(2, version)), my_world=my_world, othello_space=PersistedOthelloSpace())

        raw_spaces = d.get("spaces", {})
        if not isinstance(raw_spaces, dict):
            raw_spaces = {}

        raw_my_world = raw_spaces.get("my_world", {})
        raw_othello = raw_spaces.get("othello", {})

        my_world = PersistedPlaySpace.from_dict(raw_my_world) if isinstance(raw_my_world, dict) else PersistedPlaySpace()
        othello_space = PersistedOthelloSpace.from_dict(raw_othello) if isinstance(raw_othello, dict) else PersistedOthelloSpace()

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
        return AppState(
            current_space_id=PLAY_SPACE_MY_WORLD,
            settings=PersistedSettings(),
            inventory=PersistedInventory(),
            othello_settings=OthelloSettings(),
            my_world=PersistedPlaySpace(),
            othello_space=PersistedOthelloSpace(),
        )

@dataclass
class AppStateStore:
    project_root: Path

    def _player_store(self) -> JsonFileStore:
        p = Path(self.project_root) / "user_data" / "player_state.json"
        return JsonFileStore(path=p)

    def _world_store(self) -> JsonFileStore:
        p = Path(self.project_root) / "user_data" / "world_state.json"
        return JsonFileStore(path=p)

    def load(self) -> AppState | None:
        raw_player = self._player_store().read()
        raw_world = self._world_store().read()

        if raw_player is None and raw_world is None:
            return None

        player_file = PlayerStateFile.from_dict(raw_player or {})
        world_file = WorldStateFile.from_dict(raw_world or {})

        return AppState(
            current_space_id=normalize_play_space_id(player_file.current_space_id),
            settings=player_file.settings,
            inventory=player_file.inventory,
            othello_settings=player_file.othello_settings.normalized(),
            my_world=world_file.my_world,
            othello_space=world_file.othello_space,
        )

    def save(self, state: AppState) -> None:
        player_file = PlayerStateFile(
            version=2,
            current_space_id=normalize_play_space_id(state.current_space_id),
            settings=state.settings,
            inventory=state.inventory,
            othello_settings=state.othello_settings.normalized(),
        )
        world_file = WorldStateFile(
            version=2,
            my_world=state.my_world,
            othello_space=state.othello_space,
        )

        self._player_store().write(player_file.to_dict())
        self._world_store().write(world_file.to_dict())