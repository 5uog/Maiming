# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtGui import QImage

from ..resources.texture_atlas import TextureAtlas
from .texture_animation_catalog import AnimatedTextureTrack, default_texture_animation_tracks

@dataclass
class _RuntimeAnimatedTrack:
    logical_name: str
    base_frame: QImage
    frame_tokens: tuple[str, ...]
    frames: tuple[QImage, ...]
    frame_duration_s: float
    active_token: str | None = None
    active_index: int = -1
    active_step: int = -1

    def sequence_step_at(self, elapsed_s: float) -> int:
        duration = max(1e-6, float(self.frame_duration_s))
        return int(math.floor(float(elapsed_s) / duration))

class TextureAnimationController:
    def __init__(self, *, block_dir: Path, atlas: TextureAtlas, tracks: tuple[AnimatedTextureTrack, ...] | None = None) -> None:
        self._block_dir = Path(block_dir)
        self._atlas = atlas
        self._origin_s: float | None = None
        self._enabled: bool = True
        self._paused: bool = False
        self._paused_accum_s: float = 0.0
        self._pause_started_s: float | None = None
        self._tracks: list[_RuntimeAnimatedTrack] = []
        for track in tuple(default_texture_animation_tracks() if tracks is None else tracks):
            runtime_track = self._build_runtime_track(track)
            if runtime_track is not None:
                self._tracks.append(runtime_track)

    def _build_runtime_track(self, track: AnimatedTextureTrack) -> _RuntimeAnimatedTrack | None:
        fallback = self._load_frame(str(track.logical_name))
        if fallback is None:
            return None

        frame_tokens: list[str] = []
        frames: list[QImage] = []
        for frame_name in tuple(track.frame_sequence):
            image = self._load_frame(str(frame_name))
            frame_tokens.append(str(frame_name) if image is not None else str(track.logical_name))
            frames.append(image if image is not None else QImage(fallback))

        if not frames:
            return None
        return _RuntimeAnimatedTrack(logical_name=str(track.logical_name), base_frame=QImage(fallback), frame_tokens=tuple(frame_tokens), frames=tuple(frames), frame_duration_s=float(track.frame_duration_s))

    def set_enabled(self, enabled: bool) -> None:
        next_enabled = bool(enabled)
        if next_enabled == bool(self._enabled):
            return
        self._enabled = bool(next_enabled)
        if not bool(self._enabled):
            self._restore_base_frames()
            return
        self._origin_s = None
        self._paused_accum_s = 0.0
        self._pause_started_s = None

    def set_paused(self, paused: bool, *, elapsed_s: float) -> None:
        next_paused = bool(paused)
        now = max(0.0, float(elapsed_s))
        if next_paused == bool(self._paused):
            return
        self._paused = bool(next_paused)
        if bool(self._paused):
            self._pause_started_s = float(now)
            return
        if self._pause_started_s is not None:
            self._paused_accum_s += max(0.0, float(now) - float(self._pause_started_s))
        self._pause_started_s = None

    def _load_frame(self, texture_name: str) -> QImage | None:
        path = self._block_dir / f"{str(texture_name)}.png"
        if not path.exists():
            return None
        return self._atlas.prepared_image_from_file(path)

    def update(self, elapsed_s: float) -> None:
        if not bool(self._enabled):
            return
        now_s = max(0.0, float(elapsed_s))
        if self._origin_s is None:
            self._origin_s = float(now_s)
        if bool(self._paused):
            if self._pause_started_s is None:
                self._pause_started_s = float(now_s)
            return
        if self._pause_started_s is not None:
            self._paused_accum_s += max(0.0, float(now_s) - float(self._pause_started_s))
            self._pause_started_s = None
        now = max(0.0, float(now_s) - float(self._origin_s) - float(self._paused_accum_s))
        for track in self._tracks:
            if not track.frames:
                continue
            next_step = track.sequence_step_at(now)
            if int(next_step) == int(track.active_step):
                continue
            next_index = int(next_step % len(track.frames))
            next_token = str(track.frame_tokens[int(next_index)])
            if int(track.active_step) < 0:
                track.active_step = int(next_step)
                track.active_index = int(next_index)
                track.active_token = str(track.logical_name)
            if next_token != str(track.active_token):
                if self._atlas.replace_tile_image(str(track.logical_name), track.frames[int(next_index)]):
                    track.active_token = str(next_token)
            track.active_step = int(next_step)
            track.active_index = int(next_index)

    def _restore_base_frames(self) -> None:
        for track in self._tracks:
            self._atlas.replace_tile_image(str(track.logical_name), track.base_frame)
            track.active_token = str(track.logical_name)
            track.active_index = -1
            track.active_step = -1