# FILE: src/maiming/infrastructure/persistence/app_state_store.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, Tuple

from ...domain.config.movement_params import DEFAULT_MOVEMENT_PARAMS
from ...domain.world.world_state import WorldState
from .json_file_store import JsonFileStore

@dataclass(frozen=True)
class PersistedSettings:
    fov_deg: float = 80.0
    mouse_sens_deg_per_px: float = 0.09

    invert_x: bool = False
    invert_y: bool = False

    outline_selection: bool = True

    world_wireframe: bool = False
    shadow_enabled: bool = True

    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0

    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337
    cloud_flow_direction: str = "west_to_east"

    build_mode: bool = False
    auto_jump_enabled: bool = False
    auto_sprint_enabled: bool = False

    gravity: float = float(DEFAULT_MOVEMENT_PARAMS.gravity)
    walk_speed: float = float(DEFAULT_MOVEMENT_PARAMS.walk_speed)
    sprint_speed: float = float(DEFAULT_MOVEMENT_PARAMS.sprint_speed)
    jump_v0: float = float(DEFAULT_MOVEMENT_PARAMS.jump_v0)
    auto_jump_cooldown_s: float = float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s)

    render_distance_chunks: int = 6

    hud_visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"fov_deg": float(self.fov_deg), "mouse_sens_deg_per_px": float(self.mouse_sens_deg_per_px), "invert_x": bool(self.invert_x), "invert_y": bool(self.invert_y), "outline_selection": bool(self.outline_selection), "world_wireframe": bool(self.world_wireframe), "shadow_enabled": bool(self.shadow_enabled), "sun_az_deg": float(self.sun_az_deg), "sun_el_deg": float(self.sun_el_deg), "cloud_enabled": bool(self.cloud_enabled), "cloud_density": int(self.cloud_density), "cloud_seed": int(self.cloud_seed), "cloud_flow_direction": str(self.cloud_flow_direction), "build_mode": bool(self.build_mode), "auto_jump_enabled": bool(self.auto_jump_enabled), "auto_sprint_enabled": bool(self.auto_sprint_enabled), "gravity": float(self.gravity), "walk_speed": float(self.walk_speed), "sprint_speed": float(self.sprint_speed), "jump_v0": float(self.jump_v0), "auto_jump_cooldown_s": float(self.auto_jump_cooldown_s), "render_distance_chunks": int(self.render_distance_chunks), "hud_visible": bool(self.hud_visible)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedSettings":
        def g_float(k: str, default: float) -> float:
            v = d.get(k, default)
            try:
                return float(v)
            except Exception:
                return float(default)

        def g_int(k: str, default: int) -> int:
            v = d.get(k, default)
            try:
                return int(v)
            except Exception:
                return int(default)

        def g_bool(k: str, default: bool) -> bool:
            v = d.get(k, default)
            return bool(v) if isinstance(v, (bool, int)) else bool(default)

        def g_str(k: str, default: str) -> str:
            v = d.get(k, default)
            if v is None:
                return str(default)
            return str(v)

        rd = g_int("render_distance_chunks", 6)
        rd = int(max(2, min(16, rd)))

        return PersistedSettings(fov_deg=g_float("fov_deg", 80.0), mouse_sens_deg_per_px=g_float("mouse_sens_deg_per_px", 0.09), invert_x=g_bool("invert_x", False), invert_y=g_bool("invert_y", False), outline_selection=g_bool("outline_selection", True), world_wireframe=g_bool("world_wireframe", False), shadow_enabled=g_bool("shadow_enabled", True), sun_az_deg=g_float("sun_az_deg", 45.0), sun_el_deg=g_float("sun_el_deg", 60.0), cloud_enabled=g_bool("cloud_enabled", True), cloud_density=g_int("cloud_density", 1), cloud_seed=g_int("cloud_seed", 1337), cloud_flow_direction=g_str("cloud_flow_direction", "west_to_east"), build_mode=g_bool("build_mode", False), auto_jump_enabled=g_bool("auto_jump_enabled", False), auto_sprint_enabled=g_bool("auto_sprint_enabled", False), gravity=g_float("gravity", float(DEFAULT_MOVEMENT_PARAMS.gravity)), walk_speed=g_float("walk_speed", float(DEFAULT_MOVEMENT_PARAMS.walk_speed)), sprint_speed=g_float("sprint_speed", float(DEFAULT_MOVEMENT_PARAMS.sprint_speed)), jump_v0=g_float("jump_v0", float(DEFAULT_MOVEMENT_PARAMS.jump_v0)), auto_jump_cooldown_s=g_float("auto_jump_cooldown_s", float(DEFAULT_MOVEMENT_PARAMS.auto_jump_cooldown_s)), render_distance_chunks=int(rd), hud_visible=g_bool("hud_visible", True))

@dataclass(frozen=True)
class PersistedInventory:
    HOTBAR_SIZE: ClassVar[int] = 9

    hotbar_slots: tuple[str, ...] = ("", "", "", "", "", "", "", "", "")
    selected_hotbar_index: int = 0

    @staticmethod
    def _normalize_slots(raw: object) -> tuple[str, ...]:
        out: list[str] = []
        if isinstance(raw, list):
            for v in raw[: PersistedInventory.HOTBAR_SIZE]:
                if v is None:
                    out.append("")
                else:
                    out.append(str(v).strip())

        while len(out) < PersistedInventory.HOTBAR_SIZE:
            out.append("")

        return tuple(out[: PersistedInventory.HOTBAR_SIZE])

    def to_dict(self) -> dict[str, Any]:
        idx = int(max(0, min(self.HOTBAR_SIZE - 1, int(self.selected_hotbar_index))))
        return {"hotbar_slots": [str(v).strip() for v in self.hotbar_slots[: self.HOTBAR_SIZE]], "selected_hotbar_index": int(idx)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedInventory":
        raw_slots = d.get("hotbar_slots", [])
        slots = PersistedInventory._normalize_slots(raw_slots)

        raw_idx = d.get("selected_hotbar_index", 0)
        try:
            idx = int(raw_idx)
        except Exception:
            idx = 0
        idx = int(max(0, min(PersistedInventory.HOTBAR_SIZE - 1, idx)))

        return PersistedInventory(hotbar_slots=slots, selected_hotbar_index=int(idx))

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
    auto_jump_cooldown_s: float = 0.0
    crouch_eye_offset: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"pos": [float(self.pos_x), float(self.pos_y), float(self.pos_z)], "vel": [float(self.vel_x), float(self.vel_y), float(self.vel_z)], "yaw_deg": float(self.yaw_deg), "pitch_deg": float(self.pitch_deg), "on_ground": bool(self.on_ground), "auto_jump_cooldown_s": float(self.auto_jump_cooldown_s), "crouch_eye_offset": float(self.crouch_eye_offset)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedPlayer":
        def g_float(v: Any, default: float) -> float:
            try:
                return float(v)
            except Exception:
                return float(default)

        def g_bool(v: Any, default: bool) -> bool:
            if isinstance(v, (bool, int)):
                return bool(v)
            return bool(default)

        pos = d.get("pos", [0.0, 1.0, -10.0])
        vel = d.get("vel", [0.0, 0.0, 0.0])

        if not isinstance(pos, list) or len(pos) != 3:
            pos = [0.0, 1.0, -10.0]
        if not isinstance(vel, list) or len(vel) != 3:
            vel = [0.0, 0.0, 0.0]

        cooldown_raw = d.get("auto_jump_cooldown_s", d.get("jump_cooldown_s", 0.0))

        return PersistedPlayer(pos_x=g_float(pos[0], 0.0), pos_y=g_float(pos[1], 1.0), pos_z=g_float(pos[2], -10.0), vel_x=g_float(vel[0], 0.0), vel_y=g_float(vel[1], 0.0), vel_z=g_float(vel[2], 0.0), yaw_deg=g_float(d.get("yaw_deg", 0.0), 0.0), pitch_deg=g_float(d.get("pitch_deg", 0.0), 0.0), on_ground=g_bool(d.get("on_ground", False), False), auto_jump_cooldown_s=g_float(cooldown_raw, 0.0), crouch_eye_offset=g_float(d.get("crouch_eye_offset", 0.0), 0.0))

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
class PlayerStateFile:
    version: int = 1
    settings: PersistedSettings = PersistedSettings()
    inventory: PersistedInventory = PersistedInventory()

    def to_dict(self) -> dict[str, Any]:
        return {"version": int(self.version), "settings": self.settings.to_dict(), "inventory": self.inventory.to_dict()}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PlayerStateFile":
        if not isinstance(d, dict):
            return PlayerStateFile()

        try:
            version = int(d.get("version", 1))
        except Exception:
            version = 1

        raw_settings = d.get("settings", {})
        raw_inventory = d.get("inventory", {})

        settings = PersistedSettings.from_dict(raw_settings) if isinstance(raw_settings, dict) else PersistedSettings()
        inventory = PersistedInventory.from_dict(raw_inventory) if isinstance(raw_inventory, dict) else PersistedInventory()

        return PlayerStateFile(version=int(max(1, version)), settings=settings, inventory=inventory)

@dataclass(frozen=True)
class WorldStateFile:
    version: int = 1
    player: PersistedPlayer = PersistedPlayer()
    world: PersistedWorld = PersistedWorld(revision=0, blocks={})

    def to_dict(self) -> dict[str, Any]:
        return {"version": int(self.version), "player": self.player.to_dict(), "world": self.world.to_dict()}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "WorldStateFile":
        if not isinstance(d, dict):
            return WorldStateFile()

        try:
            version = int(d.get("version", 1))
        except Exception:
            version = 1

        raw_player = d.get("player", {})
        raw_world = d.get("world", {})

        player = PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer()
        world = PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld(revision=0, blocks={})

        return WorldStateFile(version=int(max(1, version)), player=player, world=world)

@dataclass(frozen=True)
class AppState:
    settings: PersistedSettings
    inventory: PersistedInventory
    player: PersistedPlayer
    world: PersistedWorld

    @staticmethod
    def default() -> "AppState":
        return AppState(settings=PersistedSettings(), inventory=PersistedInventory(), player=PersistedPlayer(), world=PersistedWorld(revision=0, blocks={}))

    @staticmethod
    def from_legacy_dict(d: dict[str, Any]) -> "AppState":
        if not isinstance(d, dict):
            return AppState.default()

        raw_settings = d.get("settings", {})
        raw_player = d.get("player", {})
        raw_world = d.get("world", {})

        settings = PersistedSettings.from_dict(raw_settings) if isinstance(raw_settings, dict) else PersistedSettings()
        player = PersistedPlayer.from_dict(raw_player) if isinstance(raw_player, dict) else PersistedPlayer()
        world = PersistedWorld.from_dict(raw_world) if isinstance(raw_world, dict) else PersistedWorld(revision=0, blocks={})

        return AppState(settings=settings, inventory=PersistedInventory(), player=player, world=world)

@dataclass
class AppStateStore:
    project_root: Path

    def _player_store(self) -> JsonFileStore:
        p = Path(self.project_root) / "user_data" / "player_state.json"
        return JsonFileStore(path=p)

    def _world_store(self) -> JsonFileStore:
        p = Path(self.project_root) / "user_data" / "world_state.json"
        return JsonFileStore(path=p)

    def _legacy_store(self) -> JsonFileStore:
        p = Path(self.project_root) / "user_data" / "state.json"
        return JsonFileStore(path=p)

    def load(self) -> AppState | None:
        raw_player = self._player_store().read()
        raw_world = self._world_store().read()

        if raw_player is None and raw_world is None:
            raw_legacy = self._legacy_store().read()
            if raw_legacy is None:
                return None
            return AppState.from_legacy_dict(raw_legacy)

        player_file = PlayerStateFile.from_dict(raw_player or {})
        world_file = WorldStateFile.from_dict(raw_world or {})

        return AppState(settings=player_file.settings, inventory=player_file.inventory, player=world_file.player, world=world_file.world)

    def save(self, state: AppState) -> None:
        player_file = PlayerStateFile(version=1, settings=state.settings, inventory=state.inventory)
        world_file = WorldStateFile(version=1, player=state.player, world=state.world)

        self._player_store().write(player_file.to_dict())
        self._world_store().write(world_file.to_dict())