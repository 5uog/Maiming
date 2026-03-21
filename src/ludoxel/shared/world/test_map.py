# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from .world_gen import generate_flat_world
from .world_state import WorldState

def generate_test_map(seed: int=0, params=None) -> WorldState:
    _ = int(seed)
    _ = params
    return generate_flat_world()