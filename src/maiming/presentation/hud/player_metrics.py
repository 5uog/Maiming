# FILE: src/maiming/presentation/hud/player_metrics.py
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from maiming.application.session.session_settings import SessionSettings
from maiming.domain.entities.player_entity import PlayerEntity

@dataclass(frozen=True)
class ScalarMetricSnapshot:
    current: float
    mean: float
    recent_mean: float

@dataclass(frozen=True)
class OptionalScalarMetricSnapshot:
    current: float | None
    mean: float | None
    recent_mean: float | None

@dataclass(frozen=True)
class AppliedMovementSnapshot:
    gravity: float
    walk_speed: float
    sprint_speed: float
    jump_v0: float
    auto_jump_cooldown_s: float

@dataclass(frozen=True)
class PlayerMetricsSnapshot:
    horiz_speed: ScalarMetricSnapshot
    vert_speed: ScalarMetricSnapshot
    jump_interval: OptionalScalarMetricSnapshot
    applied: AppliedMovementSnapshot
    recent_window_s: float

@dataclass
class _RollingWeightedSeries:
    window_s: float
    _samples: deque[tuple[float, float, float]] = field(default_factory=deque)
    _weighted_sum: float = 0.0
    _duration_sum: float = 0.0

    def add(self, *, now_s: float, duration_s: float, value: float) -> None:
        dur = float(max(0.0, duration_s))
        self.prune(now_s=float(now_s))
        if dur <= 1e-9:
            return
        self._samples.append((float(now_s), dur, float(value)))
        self._weighted_sum += float(value) * dur
        self._duration_sum += dur
        self.prune(now_s=float(now_s))

    def prune(self, *, now_s: float) -> None:
        cutoff = float(now_s) - float(max(0.1, self.window_s))
        while self._samples and float(self._samples[0][0]) <= cutoff:
            _ts, dur, val = self._samples.popleft()
            self._weighted_sum -= float(val) * float(dur)
            self._duration_sum -= float(dur)

        if abs(self._weighted_sum) <= 1e-12:
            self._weighted_sum = 0.0
        if self._duration_sum < 0.0:
            self._duration_sum = 0.0

    def mean(self) -> float:
        if self._duration_sum <= 1e-9:
            return 0.0
        return float(self._weighted_sum) / float(self._duration_sum)

@dataclass
class _RollingEventSeries:
    window_s: float
    _samples: deque[tuple[float, float]] = field(default_factory=deque)
    _sum: float = 0.0

    def add(self, *, now_s: float, value: float) -> None:
        self.prune(now_s=float(now_s))
        self._samples.append((float(now_s), float(value)))
        self._sum += float(value)
        self.prune(now_s=float(now_s))

    def prune(self, *, now_s: float) -> None:
        cutoff = float(now_s) - float(max(0.1, self.window_s))
        while self._samples and float(self._samples[0][0]) <= cutoff:
            _ts, val = self._samples.popleft()
            self._sum -= float(val)

        if abs(self._sum) <= 1e-12:
            self._sum = 0.0

    def mean(self) -> float | None:
        if not self._samples:
            return None
        return float(self._sum) / float(len(self._samples))

@dataclass
class PlayerMetricsTracker:
    recent_window_s: float = 3.0

    _elapsed_s: float = 0.0
    _duration_s: float = 0.0

    _h_current: float = 0.0
    _v_current: float = 0.0
    _h_weighted_sum: float = 0.0
    _v_weighted_sum: float = 0.0

    _last_jump_started_at_s: float | None = None
    _jump_interval_current: float | None = None
    _jump_interval_sum: float = 0.0
    _jump_interval_count: int = 0

    _h_recent: _RollingWeightedSeries = field(init=False, repr=False)
    _v_recent: _RollingWeightedSeries = field(init=False, repr=False)
    _jump_recent: _RollingEventSeries = field(init=False, repr=False)

    def __post_init__(self) -> None:
        w = float(max(0.5, self.recent_window_s))
        self.recent_window_s = w
        self._h_recent = _RollingWeightedSeries(window_s=w)
        self._v_recent = _RollingWeightedSeries(window_s=w)
        self._jump_recent = _RollingEventSeries(window_s=w)

    def observe_step(
        self,
        *,
        dt_s: float,
        player: PlayerEntity,
        jump_started: bool,
    ) -> None:
        dt = float(max(0.0, dt_s))
        if dt <= 1e-9:
            return

        self._elapsed_s += dt
        self._duration_s += dt

        h = math.hypot(float(player.velocity.x), float(player.velocity.z))
        v = float(player.velocity.y)

        self._h_current = float(h)
        self._v_current = float(v)
        self._h_weighted_sum += float(h) * dt
        self._v_weighted_sum += float(v) * dt

        self._h_recent.add(now_s=float(self._elapsed_s), duration_s=dt, value=float(h))
        self._v_recent.add(now_s=float(self._elapsed_s), duration_s=dt, value=float(v))
        self._jump_recent.prune(now_s=float(self._elapsed_s))

        if not bool(jump_started):
            return

        prev = self._last_jump_started_at_s
        self._last_jump_started_at_s = float(self._elapsed_s)

        if prev is None:
            return

        interval = float(self._elapsed_s) - float(prev)
        if interval < 0.0:
            return

        self._jump_interval_current = float(interval)
        self._jump_interval_sum += float(interval)
        self._jump_interval_count += 1
        self._jump_recent.add(now_s=float(self._elapsed_s), value=float(interval))

    def snapshot(self, *, settings: SessionSettings) -> PlayerMetricsSnapshot:
        dur = float(self._duration_s)

        h_mean = (float(self._h_weighted_sum) / dur) if dur > 1e-9 else float(self._h_current)
        v_mean = (float(self._v_weighted_sum) / dur) if dur > 1e-9 else float(self._v_current)

        if int(self._jump_interval_count) > 0:
            j_mean = float(self._jump_interval_sum) / float(self._jump_interval_count)
        else:
            j_mean = None

        return PlayerMetricsSnapshot(
            horiz_speed=ScalarMetricSnapshot(
                current=float(self._h_current),
                mean=float(h_mean),
                recent_mean=float(self._h_recent.mean()),
            ),
            vert_speed=ScalarMetricSnapshot(
                current=float(self._v_current),
                mean=float(v_mean),
                recent_mean=float(self._v_recent.mean()),
            ),
            jump_interval=OptionalScalarMetricSnapshot(
                current=self._jump_interval_current,
                mean=j_mean,
                recent_mean=self._jump_recent.mean(),
            ),
            applied=AppliedMovementSnapshot(
                gravity=float(settings.movement.gravity),
                walk_speed=float(settings.movement.walk_speed),
                sprint_speed=float(settings.movement.sprint_speed),
                jump_v0=float(settings.movement.jump_v0),
                auto_jump_cooldown_s=float(settings.movement.auto_jump_cooldown_s),
            ),
            recent_window_s=float(self.recent_window_s),
        )