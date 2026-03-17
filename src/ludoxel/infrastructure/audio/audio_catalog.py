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
from ...domain.blocks.sound_groups import (
    SOUND_GROUP_ANCIENT_DEBRIS,
    SOUND_GROUP_BAMBOO_WOOD,
    SOUND_GROUP_BASALT,
    SOUND_GROUP_CALCITE,
    SOUND_GROUP_CHERRY_WOOD,
    SOUND_GROUP_CORAL_BLOCK,
    SOUND_GROUP_DEEPSLATE,
    SOUND_GROUP_DEEPSLATE_BRICKS,
    SOUND_GROUP_DIRT,
    SOUND_GROUP_GILDED_BLACKSTONE,
    SOUND_GROUP_GRASS,
    SOUND_GROUP_GRAVEL,
    SOUND_GROUP_LODESTONE,
    SOUND_GROUP_METAL,
    SOUND_GROUP_MUD,
    SOUND_GROUP_NETHERRACK,
    SOUND_GROUP_NETHER_BRICKS,
    SOUND_GROUP_NETHER_GOLD_ORE,
    SOUND_GROUP_NETHER_ORE,
    SOUND_GROUP_NETHERITE,
    SOUND_GROUP_NETHER_WOOD,
    SOUND_GROUP_NYLIUM,
    SOUND_GROUP_RESIN,
    SOUND_GROUP_ROOTED_DIRT,
    SOUND_GROUP_SAND,
    SOUND_GROUP_SOUL_SAND,
    SOUND_GROUP_SOUL_SOIL,
    SOUND_GROUP_STONE,
    SOUND_GROUP_TUFF,
    SOUND_GROUP_WOOD,
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
PLAYER_EVENT_LAND_SMALL = "land_small"
PLAYER_EVENT_LAND_BIG = "land_big"
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


def _indexed_paths(prefix: str, stem: str, count: int, *, ext: str = "wav", start: int = 1) -> tuple[str, ...]:
    root = str(prefix).rstrip("/")
    base = str(stem).strip()
    return tuple(f"{root}/{base}{index}.{ext}" for index in range(int(start), int(start) + int(max(0, count))))


def _block_material_catalog(
    material: str,
    *,
    place_count: int = 4,
    break_count: int = 4,
    open_count: int = 0,
    close_count: int = 0,
    place_polyphony: int = 4,
    break_polyphony: int = 4,
    interact_polyphony: int = 2,
) -> dict[str, AudioSamplePool]:
    base = f"assets/audio/block/{material}"
    catalog: dict[str, AudioSamplePool] = {
        BLOCK_EVENT_PLACE: _pool(
            *_indexed_paths(f"{base}/place", "place", place_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=place_polyphony,
        ),
        BLOCK_EVENT_BREAK: _pool(
            *_indexed_paths(f"{base}/break", "break", break_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=break_polyphony,
        ),
    }
    if int(open_count) > 0:
        catalog[BLOCK_EVENT_INTERACT_OPEN] = _pool(
            *_indexed_paths(f"{base}/interact_open", "open", open_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=interact_polyphony,
        )
    if int(close_count) > 0:
        catalog[BLOCK_EVENT_INTERACT_CLOSE] = _pool(
            *_indexed_paths(f"{base}/interact_close", "close", close_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=interact_polyphony,
        )
    return catalog


def _step_pool(material: str, *, count: int = 6, cooldown_s: float = 0.045, max_polyphony: int = 4) -> AudioSamplePool:
    return _pool(
        *_indexed_paths(f"assets/audio/player/footstep/{material}", "step", count),
        category=AUDIO_CATEGORY_PLAYER,
        selection_mode=SELECTION_ROUND_ROBIN,
        spatial=False,
        distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
        size=0.0,
        max_polyphony=max_polyphony,
        cooldown_s=cooldown_s,
    )


BLOCK_SOUND_CATALOG: dict[str, dict[str, AudioSamplePool]] = {
    SOUND_GROUP_WOOD: _block_material_catalog(SOUND_GROUP_WOOD, open_count=2, close_count=2),
    SOUND_GROUP_CHERRY_WOOD: _block_material_catalog(SOUND_GROUP_CHERRY_WOOD, open_count=2, close_count=2),
    SOUND_GROUP_BAMBOO_WOOD: _block_material_catalog(SOUND_GROUP_BAMBOO_WOOD, open_count=2, close_count=2),
    SOUND_GROUP_NETHER_WOOD: _block_material_catalog(SOUND_GROUP_NETHER_WOOD, open_count=2, close_count=2),
    SOUND_GROUP_STONE: _block_material_catalog(SOUND_GROUP_STONE),
    SOUND_GROUP_DEEPSLATE: _block_material_catalog(SOUND_GROUP_DEEPSLATE),
    SOUND_GROUP_DEEPSLATE_BRICKS: _block_material_catalog(SOUND_GROUP_DEEPSLATE_BRICKS),
    SOUND_GROUP_TUFF: _block_material_catalog(SOUND_GROUP_TUFF),
    SOUND_GROUP_CALCITE: _block_material_catalog(SOUND_GROUP_CALCITE),
    SOUND_GROUP_BASALT: _block_material_catalog(SOUND_GROUP_BASALT),
    SOUND_GROUP_GILDED_BLACKSTONE: _block_material_catalog(SOUND_GROUP_GILDED_BLACKSTONE),
    SOUND_GROUP_LODESTONE: _block_material_catalog(SOUND_GROUP_LODESTONE),
    SOUND_GROUP_RESIN: _block_material_catalog(SOUND_GROUP_RESIN),
    SOUND_GROUP_METAL: _block_material_catalog(SOUND_GROUP_METAL),
    SOUND_GROUP_NETHERITE: _block_material_catalog(SOUND_GROUP_NETHERITE),
    SOUND_GROUP_GRASS: _block_material_catalog(SOUND_GROUP_GRASS, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_DIRT: _block_material_catalog(SOUND_GROUP_DIRT, place_count=3, break_count=6, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_ROOTED_DIRT: _block_material_catalog(SOUND_GROUP_ROOTED_DIRT, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_GRAVEL: _block_material_catalog(SOUND_GROUP_GRAVEL, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_SAND: _block_material_catalog(SOUND_GROUP_SAND, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_MUD: _block_material_catalog(SOUND_GROUP_MUD, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_NYLIUM: _block_material_catalog(SOUND_GROUP_NYLIUM, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_SOUL_SAND: _block_material_catalog(SOUND_GROUP_SOUL_SAND, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_SOUL_SOIL: _block_material_catalog(SOUND_GROUP_SOUL_SOIL, place_count=3, break_count=4, place_polyphony=3, break_polyphony=3),
    SOUND_GROUP_NETHERRACK: _block_material_catalog(SOUND_GROUP_NETHERRACK),
    SOUND_GROUP_NETHER_BRICKS: _block_material_catalog(SOUND_GROUP_NETHER_BRICKS),
    SOUND_GROUP_NETHER_ORE: _block_material_catalog(SOUND_GROUP_NETHER_ORE),
    SOUND_GROUP_NETHER_GOLD_ORE: _block_material_catalog(SOUND_GROUP_NETHER_GOLD_ORE),
    SOUND_GROUP_ANCIENT_DEBRIS: _block_material_catalog(SOUND_GROUP_ANCIENT_DEBRIS),
    SOUND_GROUP_CORAL_BLOCK: _block_material_catalog(SOUND_GROUP_CORAL_BLOCK),
}


PLAYER_SURFACE_SOUND_CATALOG: dict[str, dict[str, AudioSamplePool]] = {
    SOUND_GROUP_WOOD: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_WOOD)},
    SOUND_GROUP_CHERRY_WOOD: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_CHERRY_WOOD)},
    SOUND_GROUP_BAMBOO_WOOD: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_BAMBOO_WOOD)},
    SOUND_GROUP_NETHER_WOOD: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NETHER_WOOD)},
    SOUND_GROUP_STONE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_STONE)},
    SOUND_GROUP_DEEPSLATE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_DEEPSLATE)},
    SOUND_GROUP_DEEPSLATE_BRICKS: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_DEEPSLATE_BRICKS)},
    SOUND_GROUP_TUFF: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_TUFF)},
    SOUND_GROUP_CALCITE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_CALCITE)},
    SOUND_GROUP_BASALT: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_BASALT)},
    SOUND_GROUP_GILDED_BLACKSTONE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_GILDED_BLACKSTONE)},
    SOUND_GROUP_LODESTONE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_LODESTONE)},
    SOUND_GROUP_RESIN: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_RESIN)},
    SOUND_GROUP_METAL: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_METAL)},
    SOUND_GROUP_NETHERITE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NETHERITE)},
    SOUND_GROUP_GRASS: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_GRASS, cooldown_s=0.040)},
    SOUND_GROUP_DIRT: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_DIRT, cooldown_s=0.040)},
    SOUND_GROUP_ROOTED_DIRT: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_ROOTED_DIRT, cooldown_s=0.040)},
    SOUND_GROUP_GRAVEL: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_GRAVEL, cooldown_s=0.040)},
    SOUND_GROUP_SAND: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_SAND, cooldown_s=0.040)},
    SOUND_GROUP_MUD: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_MUD, cooldown_s=0.040)},
    SOUND_GROUP_NYLIUM: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NYLIUM, cooldown_s=0.040)},
    SOUND_GROUP_SOUL_SAND: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_SOUL_SAND, cooldown_s=0.040)},
    SOUND_GROUP_SOUL_SOIL: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_SOUL_SOIL, cooldown_s=0.040)},
    SOUND_GROUP_NETHERRACK: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NETHERRACK)},
    SOUND_GROUP_NETHER_BRICKS: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NETHER_BRICKS)},
    SOUND_GROUP_NETHER_ORE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NETHER_ORE)},
    SOUND_GROUP_NETHER_GOLD_ORE: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_NETHER_GOLD_ORE)},
    SOUND_GROUP_ANCIENT_DEBRIS: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_ANCIENT_DEBRIS)},
    SOUND_GROUP_CORAL_BLOCK: {PLAYER_EVENT_STEP: _step_pool(SOUND_GROUP_CORAL_BLOCK)},
}


PLAYER_EVENT_SOUND_CATALOG: dict[str, AudioSamplePool] = {
    PLAYER_EVENT_LAND_SMALL: _pool(
        "assets/audio/player/landing/fallsmall.wav",
        category=AUDIO_CATEGORY_PLAYER,
        selection_mode=SELECTION_RANDOM,
        spatial=False,
        distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
        size=0.0,
        max_polyphony=2,
        cooldown_s=0.015,
    ),
    PLAYER_EVENT_LAND_BIG: _pool(
        "assets/audio/player/landing/fallbig.wav",
        category=AUDIO_CATEGORY_PLAYER,
        selection_mode=SELECTION_RANDOM,
        spatial=False,
        distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF,
        size=0.0,
        max_polyphony=2,
        cooldown_s=0.015,
    ),
    PLAYER_EVENT_OTHELLO_PLACE: _pool(
        *_indexed_paths("assets/audio/player/othello/place", "place", 2),
        category=AUDIO_CATEGORY_PLAYER,
        max_polyphony=3,
    ),
    PLAYER_EVENT_OTHELLO_FLIP: _pool(
        *_indexed_paths("assets/audio/player/othello/flip", "flip", 2),
        category=AUDIO_CATEGORY_PLAYER,
        selection_mode=SELECTION_ROUND_ROBIN,
        max_polyphony=4,
    ),
}


AMBIENT_SOUND_CATALOG: dict[str, AudioSamplePool] = {
    AMBIENT_KEY_MY_WORLD: _pool(
        "assets/audio/ambient/my_world/wind1.ogg",
        "assets/audio/ambient/my_world/wind2.ogg",
        "assets/audio/ambient/my_world/wind3.ogg",
        "assets/audio/ambient/my_world/wind4.ogg",
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
