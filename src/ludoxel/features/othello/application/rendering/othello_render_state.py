# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/features/othello/application/rendering/othello_render_state.py
from __future__ import annotations

from dataclasses import dataclass

from ...domain.game.types import OthelloAnimationState


@dataclass(frozen=True)
class OthelloRenderState:
    enabled: bool = False
    board: tuple[int, ...] = ()
    legal_move_indices: tuple[int, ...] = ()
    hover_square_index: int | None = None
    last_move_index: int | None = None
    animations: tuple[OthelloAnimationState, ...] = ()
