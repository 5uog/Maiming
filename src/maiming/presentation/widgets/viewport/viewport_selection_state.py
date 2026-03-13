# FILE: src/maiming/presentation/widgets/viewport/viewport_selection_state.py
from __future__ import annotations
import time
from dataclasses import dataclass

from ....application.session.session_manager import SessionManager

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
    def _make_key(session: SessionManager, reach: float) -> tuple[float, float, float, float, float, int, float]:
        eye = session.player.eye_pos()
        return (round(float(eye.x), 4), round(float(eye.y), 4), round(float(eye.z), 4), round(float(session.player.yaw_deg), 3), round(float(session.player.pitch_deg), 3), int(session.world.revision), round(float(reach), 3))

    def refresh(self, *, session: SessionManager, reach: float, force: bool = False) -> float:
        key = self._make_key(session, float(reach))
        if (not bool(force)) and self._cache_key == key:
            return 0.0

        t0 = time.perf_counter()
        self._cache_key = key

        from maiming.domain.systems.build_system import pick_block

        eye = session.player.eye_pos()
        hit = pick_block(session.world, origin=eye, direction=session.player.view_forward(), reach=float(reach), block_registry=session.block_registry)

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