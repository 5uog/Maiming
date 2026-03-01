# FILE: src/maiming/application/session/fixed_step_runner.py
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Callable

@dataclass
class FixedStepRunner:
    step_dt: float
    on_step: Callable[[float], None]
    max_substeps: int = 8

    _accum: float = 0.0
    _last: float = 0.0

    def start(self) -> None:
        self._last = time.perf_counter()
        self._accum = 0.0

    def update(self) -> None:
        now = time.perf_counter()
        frame_dt = max(0.0, min(0.25, now - self._last))
        self._last = now
        self._accum += frame_dt

        sub = 0
        while self._accum >= self.step_dt and sub < self.max_substeps:
            self.on_step(self.step_dt)
            self._accum -= self.step_dt
            sub += 1