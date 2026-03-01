# FILE: src/maiming/presentation/config/game_loop_params.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class GameLoopParams:
    sim_hz: float = 120.0
    sim_timer_interval_ms: int = 0
    render_timer_interval_ms: int = 16

    def step_dt(self) -> float:
        hz = float(self.sim_hz)
        return 1.0 / max(hz, 1e-6)

DEFAULT_GAME_LOOP_PARAMS = GameLoopParams()