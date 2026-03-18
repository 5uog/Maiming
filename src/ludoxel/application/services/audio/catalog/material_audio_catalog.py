# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/services/audio/catalog/material_audio_catalog.py
from __future__ import annotations

from ....context.runtime.audio_preferences import (
    AUDIO_CATEGORY_BLOCK,
    AUDIO_CATEGORY_PLAYER,
)
from .....shared.domain.blocks.sound_groups import (
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
from ..audio_types import (
    AudioSamplePool,
    DEFAULT_SPATIAL_DISTANCE_CUTOFF,
    SELECTION_ROUND_ROBIN,
    indexed_paths,
    make_audio_pool,
)

BLOCK_EVENT_PLACE = "place"
BLOCK_EVENT_BREAK = "break"
BLOCK_EVENT_INTERACT_OPEN = "interact_open"
BLOCK_EVENT_INTERACT_CLOSE = "interact_close"

PLAYER_EVENT_STEP = "step"


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
        BLOCK_EVENT_PLACE: make_audio_pool(
            *indexed_paths(f"{base}/place", "place", place_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=place_polyphony,
        ),
        BLOCK_EVENT_BREAK: make_audio_pool(
            *indexed_paths(f"{base}/break", "break", break_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=break_polyphony,
        ),
    }

    if int(open_count) > 0:
        catalog[BLOCK_EVENT_INTERACT_OPEN] = make_audio_pool(
            *indexed_paths(f"{base}/interact_open", "open", open_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=interact_polyphony,
        )

    if int(close_count) > 0:
        catalog[BLOCK_EVENT_INTERACT_CLOSE] = make_audio_pool(
            *indexed_paths(f"{base}/interact_close", "close", close_count),
            category=AUDIO_CATEGORY_BLOCK,
            max_polyphony=interact_polyphony,
        )

    return catalog


def _step_pool(
    material: str,
    *,
    count: int = 6,
    cooldown_s: float = 0.045,
    max_polyphony: int = 4,
) -> AudioSamplePool:
    return make_audio_pool(
        *indexed_paths(f"assets/audio/player/footstep/{material}", "step", count),
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
    SOUND_GROUP_GRASS: _block_material_catalog(
        SOUND_GROUP_GRASS,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_DIRT: _block_material_catalog(
        SOUND_GROUP_DIRT,
        place_count=3,
        break_count=6,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_ROOTED_DIRT: _block_material_catalog(
        SOUND_GROUP_ROOTED_DIRT,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_GRAVEL: _block_material_catalog(
        SOUND_GROUP_GRAVEL,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_SAND: _block_material_catalog(
        SOUND_GROUP_SAND,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_MUD: _block_material_catalog(
        SOUND_GROUP_MUD,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_NYLIUM: _block_material_catalog(
        SOUND_GROUP_NYLIUM,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_SOUL_SAND: _block_material_catalog(
        SOUND_GROUP_SOUL_SAND,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
    SOUND_GROUP_SOUL_SOIL: _block_material_catalog(
        SOUND_GROUP_SOUL_SOIL,
        place_count=3,
        break_count=4,
        place_polyphony=3,
        break_polyphony=3,
    ),
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
