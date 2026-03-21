# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from ...runtime.state.audio_preferences import AUDIO_CATEGORY_AMBIENT
from ..audio_types import AudioSamplePool, SELECTION_ROUND_ROBIN, make_audio_pool

AMBIENT_KEY_MY_WORLD = "my_world_default"

AMBIENT_SOUND_CATALOG: dict[str, AudioSamplePool] = {AMBIENT_KEY_MY_WORLD: make_audio_pool("assets/audio/ambient/my_world/wind1.ogg", "assets/audio/ambient/my_world/wind2.ogg", "assets/audio/ambient/my_world/wind3.ogg", "assets/audio/ambient/my_world/wind4.ogg", category=AUDIO_CATEGORY_AMBIENT, selection_mode=SELECTION_ROUND_ROBIN, spatial=False, distance_cutoff=0.0, size=0.0, max_polyphony=1)}