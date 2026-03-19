# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/services/audio/catalog/player_audio_catalog.py
from __future__ import annotations

from ....context.runtime.audio_preferences import AUDIO_CATEGORY_PLAYER
from ..audio_types import (AudioSamplePool, DEFAULT_SPATIAL_DISTANCE_CUTOFF, SELECTION_RANDOM, SELECTION_ROUND_ROBIN, indexed_paths, make_audio_pool)

PLAYER_EVENT_LAND = "land"
PLAYER_EVENT_LAND_SMALL = "land_small"
PLAYER_EVENT_LAND_BIG = "land_big"
PLAYER_EVENT_OTHELLO_PLACE = "othello_place"
PLAYER_EVENT_OTHELLO_FLIP = "othello_flip"


PLAYER_EVENT_SOUND_CATALOG: dict[str, AudioSamplePool] = {PLAYER_EVENT_LAND_SMALL: make_audio_pool("assets/audio/player/landing/fallsmall.wav", category=AUDIO_CATEGORY_PLAYER, selection_mode=SELECTION_RANDOM, spatial=False, distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF, size=0.0, max_polyphony=2, cooldown_s=0.015), PLAYER_EVENT_LAND_BIG: make_audio_pool("assets/audio/player/landing/fallbig.wav", category=AUDIO_CATEGORY_PLAYER, selection_mode=SELECTION_RANDOM, spatial=False, distance_cutoff=DEFAULT_SPATIAL_DISTANCE_CUTOFF, size=0.0, max_polyphony=2, cooldown_s=0.015), PLAYER_EVENT_OTHELLO_PLACE: make_audio_pool(*indexed_paths("assets/audio/player/othello/place", "place", 2), category=AUDIO_CATEGORY_PLAYER, max_polyphony=3), PLAYER_EVENT_OTHELLO_FLIP: make_audio_pool(*indexed_paths("assets/audio/player/othello/flip", "flip", 2), category=AUDIO_CATEGORY_PLAYER, selection_mode=SELECTION_ROUND_ROBIN, max_polyphony=4)}
