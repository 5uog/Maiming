# FILE: src/maiming/infrastructure/persistence/app_state_store.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from maiming.infrastructure.persistence.json_file_store import JsonFileStore

@dataclass(frozen=True)
class PersistedSettings:
    """
    This document stores user-facing runtime parameters that are expected to persist across sessions.
    The scope is intentionally limited to values that have a clear UI mapping to avoid silently persisting
    internal tuning knobs that may change during development.
    """
    fov_deg: float = 80.0
    mouse_sens_deg_per_px: float = 0.09

    invert_x: bool = False
    invert_y: bool = False

    world_wireframe: bool = False
    shadow_enabled: bool = True

    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0

    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337

    build_mode: bool = False
    auto_jump_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "fov_deg": float(self.fov_deg),
            "mouse_sens_deg_per_px": float(self.mouse_sens_deg_per_px),
            "invert_x": bool(self.invert_x),
            "invert_y": bool(self.invert_y),
            "world_wireframe": bool(self.world_wireframe),
            "shadow_enabled": bool(self.shadow_enabled),
            "sun_az_deg": float(self.sun_az_deg),
            "sun_el_deg": float(self.sun_el_deg),
            "cloud_enabled": bool(self.cloud_enabled),
            "cloud_density": int(self.cloud_density),
            "cloud_seed": int(self.cloud_seed),
            "build_mode": bool(self.build_mode),
            "auto_jump_enabled": bool(self.auto_jump_enabled),
        }

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

        return PersistedSettings(
            fov_deg=g_float("fov_deg", 80.0),
            mouse_sens_deg_per_px=g_float("mouse_sens_deg_per_px", 0.09),
            invert_x=g_bool("invert_x", False),
            invert_y=g_bool("invert_y", False),
            world_wireframe=g_bool("world_wireframe", False),
            shadow_enabled=g_bool("shadow_enabled", True),
            sun_az_deg=g_float("sun_az_deg", 45.0),
            sun_el_deg=g_float("sun_el_deg", 60.0),
            cloud_enabled=g_bool("cloud_enabled", True),
            cloud_density=g_int("cloud_density", 1),
            cloud_seed=g_int("cloud_seed", 1337),
            build_mode=g_bool("build_mode", False),
            auto_jump_enabled=g_bool("auto_jump_enabled", False),
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
    jump_cooldown_s: float = 0.0
    crouch_eye_offset: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pos": [float(self.pos_x), float(self.pos_y), float(self.pos_z)],
            "vel": [float(self.vel_x), float(self.vel_y), float(self.vel_z)],
            "yaw_deg": float(self.yaw_deg),
            "pitch_deg": float(self.pitch_deg),
            "on_ground": bool(self.on_ground),
            "jump_cooldown_s": float(self.jump_cooldown_s),
            "crouch_eye_offset": float(self.crouch_eye_offset),
        }

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

        return PersistedPlayer(
            pos_x=g_float(pos[0], 0.0),
            pos_y=g_float(pos[1], 1.0),
            pos_z=g_float(pos[2], -10.0),
            vel_x=g_float(vel[0], 0.0),
            vel_y=g_float(vel[1], 0.0),
            vel_z=g_float(vel[2], 0.0),
            yaw_deg=g_float(d.get("yaw_deg", 0.0), 0.0),
            pitch_deg=g_float(d.get("pitch_deg", 0.0), 0.0),
            on_ground=g_bool(d.get("on_ground", False), False),
            jump_cooldown_s=g_float(d.get("jump_cooldown_s", 0.0), 0.0),
            crouch_eye_offset=g_float(d.get("crouch_eye_offset", 0.0), 0.0),
        )

@dataclass(frozen=True)
class PersistedWorld:
    revision: int
    blocks: Dict[Tuple[int, int, int], str]

    def to_dict(self) -> dict[str, Any]:
        items: list[list[Any]] = []
        for (x, y, z), s in self.blocks.items():
            items.append([int(x), int(y), int(z), str(s)])

        return {
            "revision": int(self.revision),
            "blocks": items,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PersistedWorld":
        rev = d.get("revision", 0)
        try:
            revision = int(rev)
        except Exception:
            revision = 0

        out: Dict[Tuple[int, int, int], str] = {}
        raw = d.get("blocks", [])
        if isinstance(raw, list):
            for it in raw:
                if not isinstance(it, list) or len(it) != 4:
                    continue
                try:
                    x = int(it[0])
                    y = int(it[1])
                    z = int(it[2])
                    s = str(it[3])
                except Exception:
                    continue
                out[(x, y, z)] = s

        return PersistedWorld(revision=int(max(0, revision)), blocks=out)

@dataclass(frozen=True)
class AppState:
    version: int
    settings: PersistedSettings
    player: PersistedPlayer
    world: PersistedWorld

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": int(self.version),
            "settings": self.settings.to_dict(),
            "player": self.player.to_dict(),
            "world": self.world.to_dict(),
        }

    @staticmethod
    def default() -> "AppState":
        return AppState(
            version=2,
            settings=PersistedSettings(),
            player=PersistedPlayer(),
            world=PersistedWorld(revision=0, blocks={}),
        )

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AppState":
        ver = d.get("version", 1)
        try:
            version = int(ver)
        except Exception:
            version = 1

        sd = d.get("settings", {})
        pd = d.get("player", {})
        wd = d.get("world", {})

        settings = PersistedSettings.from_dict(sd) if isinstance(sd, dict) else PersistedSettings()
        player = PersistedPlayer.from_dict(pd) if isinstance(pd, dict) else PersistedPlayer()
        world = PersistedWorld.from_dict(wd) if isinstance(wd, dict) else PersistedWorld(revision=0, blocks={})

        v = int(max(1, version))
        return AppState(version=v, settings=settings, player=player, world=world)

@dataclass
class AppStateStore:
    project_root: Path

    def _store(self) -> JsonFileStore:
        p = Path(self.project_root) / "user_data" / "state.json"
        return JsonFileStore(path=p)

    def load(self) -> AppState | None:
        raw = self._store().read()
        if raw is None:
            return None
        return AppState.from_dict(raw)

    def save(self, state: AppState) -> None:
        self._store().write(state.to_dict())