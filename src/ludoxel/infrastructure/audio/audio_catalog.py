# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/audio/audio_catalog.py
from __future__ import annotations

from dataclasses import dataclass

from ...application.session.audio_preferences import (
    AUDIO_CATEGORY_AMBIENT,
    AUDIO_CATEGORY_BLOCK,
    AUDIO_CATEGORY_PLAYER,
)

SELECTION_RANDOM = "random"
SELECTION_ROUND_ROBIN = "round_robin"

DEFAULT_SPATIAL_DISTANCE_CUTOFF = 16.0
DEFAULT_SPATIAL_SIZE = 0.75

BLOCK_EVENT_PLACE = "place"
BLOCK_EVENT_BREAK = "break"
BLOCK_EVENT_INTERACT_OPEN = "interact_open"
BLOCK_EVENT_INTERACT_CLOSE = "interact_close"

PLAYER_EVENT_STEP = "step"
PLAYER_EVENT_LAND = "land"
PLAYER_EVENT_OTHELLO_PLACE = "othello_place"
PLAYER_EVENT_OTHELLO_FLIP = "othello_flip"

AMBIENT_KEY_MY_WORLD = "my_world_default"


@dataclass(frozen=True)
class AudioSamplePool:
    relative_paths: tuple[str, ...]
    category: str
    selection_mode: str
    spatial: bool = True
    distance_cutoff: float = DEFAULT_SPATIAL_DISTANCE_CUTOFF
    size: float = DEFAULT_SPATIAL_SIZE
    max_polyphony: int = 4
    cooldown_s: float = 0.0


def _pool(
    *paths: str,
    category: str,
    selection_mode: str = SELECTION_RANDOM,
    spatial: bool = True,
    distance_cutoff: float = DEFAULT_SPATIAL_DISTANCE_CUTOFF,
    size: float = DEFAULT_SPATIAL_SIZE,
    max_polyphony: int = 4,
    cooldown_s: float = 0.0,
) -> AudioSamplePool:
    return AudioSamplePool(
        relative_paths=tuple(str(path) for path in paths),
        category=str(category),
        selection_mode=str(selection_mode),
        spatial=bool(spatial),
        distance_cutoff=float(distance_cutoff),
        size=float(size),
        max_polyphony=int(max(1, max_polyphony)),
        cooldown_s=max(0.0, float(cooldown_s)),
    )


BLOCK_SOUND_CATALOG: dict[str, dict[str, AudioSamplePool]] = {
    "wood": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/wood/place/wood1.wav",
            "assets/audio/block/wood/place/wood2.wav",
            "assets/audio/block/wood/place/wood3.wav",
            "assets/audio/block/wood/place/wood4.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/wood/break/example_01.wav",
            "assets/audio/block/wood/break/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/wood/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/wood/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "stone": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/stone/place/example_01.wav",
            "assets/audio/block/stone/place/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/stone/break/example_01.wav",
            "assets/audio/block/stone/break/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/stone/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/stone/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "prismarine": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/prismarine/place/example_01.wav",
            "assets/audio/block/prismarine/place/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/prismarine/break/example_01.wav",
            "assets/audio/block/prismarine/break/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/prismarine/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/prismarine/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "magma": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/magma/place/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/magma/break/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/magma/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/magma/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "metal": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/metal/place/example_01.wav",
            "assets/audio/block/metal/place/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/metal/break/example_01.wav",
            "assets/audio/block/metal/break/example_02.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=4,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/metal/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/metal/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "grass": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/grass/place/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/grass/break/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/grass/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/grass/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "dirt": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/dirt/place/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/dirt/break/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/dirt/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/dirt/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "sand": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/sand/place/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/sand/break/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/sand/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/sand/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
    "gravel": {
        BLOCK_EVENT_PLACE: _pool(
            "assets/audio/block/gravel/place/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_BREAK: _pool(
            "assets/audio/block/gravel/break/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=3,
        ),
        BLOCK_EVENT_INTERACT_OPEN: _pool(
            "assets/audio/block/gravel/interact_open/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
        BLOCK_EVENT_INTERACT_CLOSE: _pool(
            "assets/audio/block/gravel/interact_close/example_01.wav",
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=2,
        ),
    },
}


PLAYER_SURFACE_SOUND_CATALOG: dict[str, dict[str, AudioSamplePool]] = {
    "wood": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/wood/example_01.wav",
            "assets/audio/player/footstep/wood/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/wood/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "stone": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/stone/example_01.wav",
            "assets/audio/player/footstep/stone/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/stone/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "prismarine": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/prismarine/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/prismarine/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "magma": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/magma/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/magma/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "metal": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/metal/example_01.wav",
            "assets/audio/player/footstep/metal/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/metal/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "grass": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/grass/example_01.wav",
            "assets/audio/player/footstep/grass/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/grass/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "dirt": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/dirt/example_01.wav",
            "assets/audio/player/footstep/dirt/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/dirt/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "sand": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/sand/example_01.wav",
            "assets/audio/player/footstep/sand/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/sand/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
    "gravel": {
        PLAYER_EVENT_STEP: _pool(
            "assets/audio/player/footstep/gravel/example_01.wav",
            "assets/audio/player/footstep/gravel/example_02.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_ROUND_ROBIN,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=4,
            cooldown_s=0.085,
        ),
        PLAYER_EVENT_LAND: _pool(
            "assets/audio/player/landing/gravel/example_01.wav",
            category=AUDIO_CATEGORY_PLAYER,
            selection_mode=SELECTION_RANDOM,
            spatial=False,
            distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
            size=0.0,
            max_polyphony=2,
            cooldown_s=0.020,
        ),
    },
}


PLAYER_EVENT_SOUND_CATALOG: dict[str, AudioSamplePool] = {
    PLAYER_EVENT_OTHELLO_PLACE: _pool(
        "assets/audio/player/othello/place/example_01.wav",
        "assets/audio/player/othello/place/example_02.wav",
        category=AUDIO_CATEGORY_PLAYER,
        max_polyphony=3,
    ),
    PLAYER_EVENT_OTHELLO_FLIP: _pool(
        "assets/audio/player/othello/flip/example_01.wav",
        "assets/audio/player/othello/flip/example_02.wav",
        category=AUDIO_CATEGORY_PLAYER,
        selection_mode=SELECTION_ROUND_ROBIN,
        max_polyphony=4,
    ),
}


AMBIENT_SOUND_CATALOG: dict[str, AudioSamplePool] = {
    AMBIENT_KEY_MY_WORLD: _pool(
        "assets/audio/ambient/my_world/example_loop_01.ogg",
        "assets/audio/ambient/my_world/example_loop_02.ogg",
        category=AUDIO_CATEGORY_AMBIENT,
        selection_mode=SELECTION_ROUND_ROBIN,
        spatial=False,
        distance_cutoff=0.0,
        size=0.0,
        max_polyphony=1,
    ),
}


def iter_named_pools() -> tuple[tuple[str, AudioSamplePool], ...]:
    entries: list[tuple[str, AudioSamplePool]] = []

    for sound_group, group_catalog in BLOCK_SOUND_CATALOG.items():
        for event_name, pool in group_catalog.items():
            entries.append((f"block:{sound_group}:{event_name}", pool))

    for sound_group, group_catalog in PLAYER_SURFACE_SOUND_CATALOG.items():
        for event_name, pool in group_catalog.items():
            entries.append((f"player:{sound_group}:{event_name}", pool))

    for event_name, pool in PLAYER_EVENT_SOUND_CATALOG.items():
        entries.append((f"player_event:{event_name}", pool))

    for ambient_key, pool in AMBIENT_SOUND_CATALOG.items():
        entries.append((f"ambient:{ambient_key}", pool))

    return tuple(entries)
