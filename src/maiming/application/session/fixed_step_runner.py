# FILE: src/maiming/application/session/fixed_step_runner.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import time

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

        if float(self._last) <= 0.0:
            self._last = now
            self._accum = 0.0
            return

        step = float(self.step_dt)
        if step <= 0.0:
            self._last = now
            self._accum = 0.0
            return

        frame_dt = max(0.0, min(0.25, now - self._last))
        self._last = now
        self._accum += frame_dt

        sub = 0
        limit = int(max(1, int(self.max_substeps)))

        while self._accum >= step and sub < limit:
            self.on_step(step)
            self._accum -= step
            sub += 1

        if self._accum >= step:
            self._accum = min(float(self._accum), step)