# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/viewport/viewport_selection_state.py
from __future__ import annotations

import time
from dataclasses import dataclass

from ....application.session.session_manager import SessionManager
from ....core.math.vec3 import Vec3
from ....core.math.view_angles import forward_from_yaw_pitch_deg

SelectionTarget = tuple[int, int, int, str]


@dataclass
class ViewportSelectionState:
    _target: SelectionTarget | None = None
    _cache_key: tuple[float, float, float, float, float, int, float] | None = None

    def target(self) -> SelectionTarget | None:
        return self._target

    def invalidate(self) -> None:
        self._cache_key = None
        self._target = None

    @staticmethod
    def _make_key(session: SessionManager, reach: float, *, eye: Vec3 | None=None, yaw_deg: float | None=None, pitch_deg: float | None=None) -> tuple[float, float, float, float, float, int, float]:
        eye_vec = session.player.eye_pos() if eye is None else eye
        yaw = float(session.player.yaw_deg) if yaw_deg is None else float(yaw_deg)
        pitch = float(session.player.pitch_deg) if pitch_deg is None else float(pitch_deg)
        return (round(float(eye_vec.x), 4), round(float(eye_vec.y), 4), round(float(eye_vec.z), 4), round(float(yaw), 3), round(float(pitch), 3), int(session.world.revision), round(float(reach), 3))

    def refresh(self, *, session: SessionManager, reach: float, eye: Vec3 | None=None, yaw_deg: float | None=None, pitch_deg: float | None=None, force: bool=False) -> float:
        key = self._make_key(session, float(reach), eye=eye, yaw_deg=yaw_deg, pitch_deg=pitch_deg)
        if (not bool(force)) and self._cache_key == key:
            return 0.0

        t0 = time.perf_counter()
        self._cache_key = key

        from ludoxel.domain.systems.build_system import pick_block

        origin = session.player.eye_pos() if eye is None else eye
        yaw = float(session.player.yaw_deg) if yaw_deg is None else float(yaw_deg)
        pitch = float(session.player.pitch_deg) if pitch_deg is None else float(pitch_deg)
        hit = pick_block(session.world, origin=origin, direction=forward_from_yaw_pitch_deg(yaw, pitch), reach=float(reach), block_registry=session.block_registry)

        if hit is None:
            self._target = None
            return float((time.perf_counter() - t0) * 1000.0)

        hx, hy, hz = hit.hit
        st = session.world.blocks.get((int(hx), int(hy), int(hz)))
        if st is None:
            self._target = None
            return float((time.perf_counter() - t0) * 1000.0)

        self._target = (int(hx), int(hy), int(hz), str(st))
        return float((time.perf_counter() - t0) * 1000.0)
