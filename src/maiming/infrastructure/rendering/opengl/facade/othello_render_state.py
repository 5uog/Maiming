# FILE: src/maiming/infrastructure/rendering/opengl/facade/othello_render_state.py
from __future__ import annotations
from dataclasses import dataclass

from .....domain.othello.types import OthelloAnimationState

@dataclass(frozen=True)
class OthelloRenderState:
    enabled: bool = False
    board: tuple[int, ...] = ()
    legal_move_indices: tuple[int, ...] = ()
    hover_square_index: int | None = None
    last_move_index: int | None = None
    animations: tuple[OthelloAnimationState, ...] = ()