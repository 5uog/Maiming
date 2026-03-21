# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import math
import random
import time

from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect

from ..runtime.state.audio_preferences import AUDIO_CATEGORY_AMBIENT, AudioPreferences
from ...shared.math.vec3 import Vec3
from ...shared.blocks.registry.block_registry import BlockRegistry
from ...shared.blocks.sound_groups import DEFAULT_BLOCK_SOUND_GROUP, iter_sound_group_candidates
from ...shared.blocks.state.state_codec import parse_state
from ...shared.blocks.state.state_values import prop_as_bool
from ...shared.world.play_space import is_my_world_space
from .catalog.ambient_audio_catalog import AMBIENT_KEY_MY_WORLD, AMBIENT_SOUND_CATALOG
from .audio_types import AudioSamplePool, SELECTION_ROUND_ROBIN
from .catalog.material_audio_catalog import BLOCK_EVENT_BREAK, BLOCK_EVENT_INTERACT_CLOSE, BLOCK_EVENT_INTERACT_OPEN, BLOCK_EVENT_PLACE, BLOCK_SOUND_CATALOG, PLAYER_EVENT_STEP, PLAYER_SURFACE_SOUND_CATALOG
from .catalog.player_audio_catalog import PLAYER_EVENT_LAND, PLAYER_EVENT_LAND_BIG, PLAYER_EVENT_LAND_SMALL, PLAYER_EVENT_SOUND_CATALOG

@dataclass
class _EffectVoiceSlot:
    effect: QSoundEffect
    source_key: str

@dataclass
class _PreparedSource:
    url: QUrl
    source_key: str
    desired_slots: int = 1
    slots: list[_EffectVoiceSlot] = field(default_factory=list)
    cursor: int = 0

class AudioManager(QObject):
    def __init__(self, *, project_root: Path, block_registry: BlockRegistry, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._root = Path(project_root)
        self._block_registry = block_registry
        self._preferences = AudioPreferences()

        self._ambient_player: QMediaPlayer | None = None
        self._ambient_output: QAudioOutput | None = None
        self._ambient_key: str | None = None
        self._ambient_source_key: str = ""
        self._ambient_enabled: bool = False
        self._ambient_space_id: str = ""

        self._pool_specs: dict[str, AudioSamplePool] = self._collect_named_pools()
        self._resolved_urls: dict[str, tuple[QUrl, ...]] = {}
        self._prepared_sources: dict[str, list[_PreparedSource]] = {}
        self._round_robin_index: dict[str, int] = {}
        self._random = random.Random(91357)

        self._listener_pose: tuple[float, float, float, float, float, float] | None = None
        self._sound_group_cache: dict[str, str] = {}
        self._pool_throttle_until_s: dict[str, float] = {}
        self._effects_primed: bool = False

        self._listener_linear_epsilon = 0.05
        self._listener_angular_epsilon_deg = 1.0

        self._small_landing_threshold_blocks = 6.0
        self._big_landing_threshold_blocks = 12.0

        self._build_source_cache()
        self.prime_effects()

    def shutdown(self) -> None:
        if self._ambient_player is not None:
            self._ambient_player.stop()
            self._ambient_player.deleteLater()
            self._ambient_player = None

        if self._ambient_output is not None:
            self._ambient_output.deleteLater()
            self._ambient_output = None

        for prepared_group in tuple(self._prepared_sources.values()):
            for prepared in tuple(prepared_group):
                for slot in tuple(prepared.slots):
                    slot.effect.stop()
                    slot.effect.deleteLater()

        self._prepared_sources.clear()
        self._ambient_key = None
        self._ambient_source_key = ""
        self._listener_pose = None
        self._pool_throttle_until_s.clear()
        self._effects_primed = False

    def set_preferences(self, preferences: AudioPreferences) -> None:
        self._preferences = preferences.normalized()

        if self._ambient_output is not None:
            self._ambient_output.setVolume(float(self._preferences.volume_for(AUDIO_CATEGORY_AMBIENT)))

        for pool_key, prepared_group in self._prepared_sources.items():
            pool = self._pool_specs.get(str(pool_key))
            if pool is None:
                continue

            base_volume = float(self._preferences.volume_for(pool.category))
            for prepared in tuple(prepared_group):
                for slot in tuple(prepared.slots):
                    slot.effect.setVolume(base_volume)

        self._sync_ambient_sound()

    def prime_effects(self) -> None:
        if self._effects_primed:
            return

        for pool_key, pool in self._pool_specs.items():
            if str(pool.category) == AUDIO_CATEGORY_AMBIENT:
                continue

            prepared_sources = self._ensure_prepared_sources(str(pool_key), pool)
            if not prepared_sources:
                continue

            base_volume = float(self._preferences.volume_for(pool.category))
            for prepared in tuple(prepared_sources):
                self._ensure_effect_slots(prepared, desired_slots=int(prepared.desired_slots), base_volume=float(base_volume))

        self._effects_primed = True

    def cache_listener_pose(self, *, eye: Vec3, yaw_deg: float, pitch_deg: float, roll_deg: float = 0.0) -> None:
        new_pose = (float(eye.x), float(eye.y), float(eye.z), float(yaw_deg), float(pitch_deg), float(roll_deg))
        if self._listener_pose is not None and self._pose_almost_equal(self._listener_pose, new_pose):
            return
        self._listener_pose = new_pose

    def update_listener(self, *, eye: Vec3, yaw_deg: float, pitch_deg: float, roll_deg: float = 0.0) -> None:
        self.cache_listener_pose(eye=eye, yaw_deg=float(yaw_deg), pitch_deg=float(pitch_deg), roll_deg=float(roll_deg))

    def set_ambient_active(self, *, current_space_id: str, enabled: bool) -> None:
        self._ambient_space_id = str(current_space_id)
        self._ambient_enabled = bool(enabled)
        self._sync_ambient_sound()

    def play_interaction(self, *, action: str | None, block_state: str | None, position: tuple[int, int, int] | None) -> None:
        if action is None or block_state is None or position is None:
            return

        sound_group = self.sound_group_for_block_state(str(block_state))

        if action == "interact":
            _base_id, props = parse_state(str(block_state))
            is_open = prop_as_bool(props, "open", False)
            action = (BLOCK_EVENT_INTERACT_OPEN if bool(is_open) else BLOCK_EVENT_INTERACT_CLOSE)

        if action in {BLOCK_EVENT_INTERACT_OPEN, BLOCK_EVENT_INTERACT_CLOSE}:
            self.play_block_action(action=str(action), sound_group=sound_group, position=tuple(position))
            return

        if action in {BLOCK_EVENT_PLACE, BLOCK_EVENT_BREAK}:
            self.play_block_action(action=str(action), sound_group=sound_group, position=tuple(position))

    def play_block_action(self, *, action: str, sound_group: str, position: tuple[int, int, int]) -> None:
        world_position = self._block_center(tuple(position))

        for candidate_group in iter_sound_group_candidates(str(sound_group)):
            group_catalog = BLOCK_SOUND_CATALOG.get(str(candidate_group))
            pool = None if group_catalog is None else group_catalog.get(str(action))
            if pool is None:
                continue
            if self._play_pool(pool_key=f"block:{candidate_group}:{action}", pool=pool, position=world_position):
                return

    def play_surface_event(self, *, event_name: str, support_block_state: str | None, position: tuple[int, int, int] | None, fall_distance_blocks: float | None = None) -> None:
        if support_block_state is None or position is None:
            return

        sound_group = self.sound_group_for_block_state(str(support_block_state))
        world_position = self._block_center(tuple(position))

        if str(event_name) == PLAYER_EVENT_LAND:
            self._play_landing_event(sound_group=sound_group, position=world_position, fall_distance_blocks=fall_distance_blocks)
            return

        if str(event_name) != PLAYER_EVENT_STEP:
            return

        self._play_surface_step(sound_group=sound_group, position=world_position)

    def play_othello_event(self, *, event_name: str, position: tuple[float, float, float]) -> None:
        pool = PLAYER_EVENT_SOUND_CATALOG.get(str(event_name))
        if pool is None:
            return

        self._play_pool(pool_key=f"player_event:{event_name}", pool=pool, position=Vec3(float(position[0]), float(position[1]), float(position[2])))

    def sound_group_for_block_state(self, block_state_or_id: str) -> str:
        base_id, _props = parse_state(str(block_state_or_id))
        cache_key = str(base_id).strip()
        cached = self._sound_group_cache.get(cache_key)
        if cached is not None:
            return cached

        definition = self._block_registry.get(str(base_id))
        sound_group = (DEFAULT_BLOCK_SOUND_GROUP if definition is None else str(definition.sound_group_name()).strip())
        normalized = sound_group if sound_group else DEFAULT_BLOCK_SOUND_GROUP
        self._sound_group_cache[cache_key] = normalized
        return normalized

    def _collect_named_pools(self) -> dict[str, AudioSamplePool]:
        entries: dict[str, AudioSamplePool] = {}

        for sound_group, group_catalog in BLOCK_SOUND_CATALOG.items():
            for event_name, pool in group_catalog.items():
                entries[f"block:{sound_group}:{event_name}"] = pool

        for sound_group, group_catalog in PLAYER_SURFACE_SOUND_CATALOG.items():
            for event_name, pool in group_catalog.items():
                entries[f"player:{sound_group}:{event_name}"] = pool

        for event_name, pool in PLAYER_EVENT_SOUND_CATALOG.items():
            entries[f"player_event:{event_name}"] = pool

        for ambient_key, pool in AMBIENT_SOUND_CATALOG.items():
            entries[f"ambient:{ambient_key}"] = pool

        return entries

    def _landing_event_name(self, fall_distance_blocks: float | None) -> str | None:
        distance = 0.0 if fall_distance_blocks is None else max(0.0, float(fall_distance_blocks))

        if distance >= float(self._big_landing_threshold_blocks):
            return PLAYER_EVENT_LAND_BIG

        if distance >= float(self._small_landing_threshold_blocks):
            return PLAYER_EVENT_LAND_SMALL

        return None

    def _play_landing_event(self, *, sound_group: str, position: Vec3, fall_distance_blocks: float | None) -> None:
        event_name = self._landing_event_name(fall_distance_blocks)

        if event_name is None:
            self._play_surface_step(sound_group=str(sound_group), position=position)
            return

        pool = PLAYER_EVENT_SOUND_CATALOG.get(str(event_name))
        if pool is None:
            return

        self._play_pool(pool_key=f"player_event:{event_name}", pool=pool, position=position)

    def _play_surface_step(self, *, sound_group: str, position: Vec3) -> None:
        for candidate_group in iter_sound_group_candidates(str(sound_group)):
            group_catalog = PLAYER_SURFACE_SOUND_CATALOG.get(str(candidate_group))
            pool = None if group_catalog is None else group_catalog.get(PLAYER_EVENT_STEP)
            if pool is None:
                continue
            if self._play_pool(pool_key=f"player:{candidate_group}:{PLAYER_EVENT_STEP}", pool=pool, position=position):
                return

    def _pose_almost_equal(self, left: tuple[float, float, float, float, float, float], right: tuple[float, float, float, float, float, float]) -> bool:
        lx, ly, lz, lyaw, lpitch, lroll = left
        rx, ry, rz, ryaw, rpitch, rroll = right

        linear_eps = float(self._listener_linear_epsilon)
        angular_eps = float(self._listener_angular_epsilon_deg)

        return (abs(lx - rx) <= linear_eps and abs(ly - ry) <= linear_eps and abs(lz - rz) <= linear_eps and abs(lyaw - ryaw) <= angular_eps and abs(lpitch - rpitch) <= angular_eps and abs(lroll - rroll) <= angular_eps)

    def _block_center(self, position: tuple[int, int, int]) -> Vec3:
        return Vec3(float(position[0]) + 0.5, float(position[1]) + 0.5, float(position[2]) + 0.5)

    def _build_source_cache(self) -> None:
        for pool_key, pool in self._pool_specs.items():
            self._resolved_urls[str(pool_key)] = self._resolve_existing_urls(pool)

    def _resolve_existing_urls(self, pool: AudioSamplePool) -> tuple[QUrl, ...]:
        urls: list[QUrl] = []
        for relative_path in tuple(pool.relative_paths):
            candidate = self._root / Path(relative_path)
            if candidate.is_file():
                urls.append(QUrl.fromLocalFile(str(candidate)))
        return tuple(urls)

    @staticmethod
    def _source_key_for_url(url: QUrl) -> str:
        return str(url.toString())

    def _ensure_prepared_sources(self, pool_key: str, pool: AudioSamplePool) -> list[_PreparedSource]:
        cached = self._prepared_sources.get(str(pool_key))
        if cached is not None:
            return cached

        urls = self._resolved_urls.get(str(pool_key))
        if urls is None:
            urls = self._resolve_existing_urls(pool)
            self._resolved_urls[str(pool_key)] = urls

        desired_slots = self._slot_budget_per_source(pool, source_count=len(urls))
        prepared = [_PreparedSource(url=url, source_key=self._source_key_for_url(url), desired_slots=int(desired_slots)) for url in tuple(urls)]
        self._prepared_sources[str(pool_key)] = prepared
        return prepared

    def _pick_prepared_source(self, pool_key: str, pool: AudioSamplePool, prepared_sources: list[_PreparedSource]) -> _PreparedSource | None:
        if not prepared_sources:
            return None

        if str(pool.selection_mode) == SELECTION_ROUND_ROBIN:
            cursor = int(self._round_robin_index.get(str(pool_key), -1)) + 1
            idx = int(cursor % len(prepared_sources))
            self._round_robin_index[str(pool_key)] = idx
            return prepared_sources[idx]

        return prepared_sources[int(self._random.randrange(len(prepared_sources)))]

    def _admit_pool_play(self, *, pool_key: str, pool: AudioSamplePool) -> bool:
        if float(pool.cooldown_s) <= 1e-9:
            return True

        now = time.perf_counter()
        until_s = float(self._pool_throttle_until_s.get(str(pool_key), 0.0))
        if now < until_s:
            return False

        self._pool_throttle_until_s[str(pool_key)] = now + float(pool.cooldown_s)
        return True

    def _listener_within_cutoff(self, *, position: Vec3, cutoff: float) -> bool:
        if cutoff <= 1e-6:
            return True

        pose = self._listener_pose
        if pose is None:
            return True

        px, py, pz, _yaw_deg, _pitch_deg, _roll_deg = pose
        dx = float(position.x) - float(px)
        dy = float(position.y) - float(py)
        dz = float(position.z) - float(pz)
        return (dx * dx + dy * dy + dz * dz) <= float(cutoff * cutoff)

    @staticmethod
    def _slot_budget_per_source(pool: AudioSamplePool, *, source_count: int) -> int:
        total_sources = max(1, int(source_count))
        total_polyphony = max(1, int(pool.max_polyphony))
        return max(1, int(math.ceil(float(total_polyphony) / float(total_sources))))

    def _ensure_effect_slots(self, prepared: _PreparedSource, *, desired_slots: int, base_volume: float) -> None:
        while len(prepared.slots) < int(desired_slots):
            effect = QSoundEffect(self)
            effect.setLoopCount(1)
            effect.setSource(prepared.url)
            effect.setVolume(float(base_volume))
            prepared.slots.append(_EffectVoiceSlot(effect=effect, source_key=str(prepared.source_key)))

    def _next_effect_slot(self, prepared: _PreparedSource, *, desired_slots: int, base_volume: float) -> _EffectVoiceSlot | None:
        self._ensure_effect_slots(prepared, desired_slots=int(desired_slots), base_volume=float(base_volume))
        if not prepared.slots:
            return None

        total_slots = len(prepared.slots)
        start_index = int(prepared.cursor % total_slots)

        for offset in range(total_slots):
            idx = int((start_index + offset) % total_slots)
            slot = prepared.slots[idx]
            if slot.effect.isLoaded():
                prepared.cursor = int((idx + 1) % total_slots)
                return slot

        return None

    def _play_pool(self, *, pool_key: str, pool: AudioSamplePool, position: Vec3) -> bool:
        base_volume = float(self._preferences.volume_for(pool.category))
        if base_volume <= 1e-6:
            return False

        if not self._admit_pool_play(pool_key=str(pool_key), pool=pool):
            return False

        if bool(pool.spatial) and float(pool.distance_cutoff) > 1e-6:
            if not self._listener_within_cutoff(position=position, cutoff=float(pool.distance_cutoff)):
                return False

        prepared_sources = self._ensure_prepared_sources(str(pool_key), pool)
        if not prepared_sources:
            return False

        prepared = self._pick_prepared_source(str(pool_key), pool, prepared_sources)
        if prepared is None:
            return False

        desired_slots = self._slot_budget_per_source(pool, source_count=len(prepared_sources))
        slot = self._next_effect_slot(prepared, desired_slots=int(desired_slots), base_volume=float(base_volume))
        if slot is None:
            return False

        if slot.effect.isPlaying():
            slot.effect.stop()
        slot.effect.setVolume(float(base_volume))
        slot.effect.play()
        return True

    def _ensure_ambient_player(self) -> QMediaPlayer:
        if self._ambient_player is not None:
            return self._ambient_player

        output = QAudioOutput(self)
        output.setVolume(float(self._preferences.volume_for(AUDIO_CATEGORY_AMBIENT)))

        player = QMediaPlayer(self)
        player.setAudioOutput(output)
        player.setLoops(1)
        player.mediaStatusChanged.connect(self._on_ambient_media_status_changed)

        self._ambient_output = output
        self._ambient_player = player
        return player

    def _ambient_desired_key(self) -> str | None:
        if bool(self._ambient_enabled) and is_my_world_space(self._ambient_space_id):
            return AMBIENT_KEY_MY_WORLD
        return None

    def _sync_ambient_sound(self) -> None:
        desired_key = self._ambient_desired_key()
        volume = float(self._preferences.volume_for(AUDIO_CATEGORY_AMBIENT))

        if desired_key is None or volume <= 1e-6:
            if self._ambient_player is not None:
                self._ambient_player.stop()
            self._ambient_key = None
            self._ambient_source_key = ""
            return

        player = self._ensure_ambient_player()
        if self._ambient_output is not None:
            self._ambient_output.setVolume(volume)

        if self._ambient_key != str(desired_key):
            self._ambient_key = str(desired_key)
            self._ambient_source_key = ""
            self._start_next_ambient_source()
            return

        if player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self._start_next_ambient_source()

    def _pick_existing_url(self, pool_key: str, pool: AudioSamplePool) -> QUrl | None:
        urls = self._resolved_urls.get(str(pool_key))
        if urls is None:
            urls = self._resolve_existing_urls(pool)
            self._resolved_urls[str(pool_key)] = urls

        if not urls:
            return None

        if str(pool.selection_mode) == SELECTION_ROUND_ROBIN:
            cursor = int(self._round_robin_index.get(str(pool_key), -1)) + 1
            idx = int(cursor % len(urls))
            self._round_robin_index[str(pool_key)] = idx
            return urls[idx]

        return urls[int(self._random.randrange(len(urls)))]

    def _start_next_ambient_source(self) -> None:
        if self._ambient_key is None:
            return

        pool = AMBIENT_SOUND_CATALOG.get(str(self._ambient_key))
        if pool is None:
            return

        url = self._pick_existing_url(f"ambient:{self._ambient_key}", pool)
        if url is None:
            if self._ambient_player is not None:
                self._ambient_player.stop()
            self._ambient_source_key = ""
            return

        player = self._ensure_ambient_player()
        source_key = self._source_key_for_url(url)

        player.stop()
        if self._ambient_source_key != source_key:
            player.setSource(url)
            self._ambient_source_key = source_key
        else:
            player.setPosition(0)
        player.play()

    def _on_ambient_media_status_changed(self, status) -> None:
        if self._ambient_key is None:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._start_next_ambient_source()