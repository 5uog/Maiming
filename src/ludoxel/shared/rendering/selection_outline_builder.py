# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..blocks.block_definition import BlockDefinition
from .visible_faces import iter_visible_faces

GetState = Callable[[int, int, int], str | None]
DefLookup = Callable[[str], BlockDefinition | None]

@dataclass(frozen=True)
class SelectionOutlineBuilder:
    def_lookup: DefLookup

    @staticmethod
    def _quant(v: float, q: float=1e-6) -> int:
        return int(round(float(v) / float(q)))

    def _edge_key(self, a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[int, ...]:
        qa = (self._quant(a[0]), self._quant(a[1]), self._quant(a[2]))
        qb = (self._quant(b[0]), self._quant(b[1]), self._quant(b[2]))

        if qa <= qb:
            return (qa[0], qa[1], qa[2], qb[0], qb[1], qb[2])

        return (qb[0], qb[1], qb[2], qa[0], qa[1], qa[2])

    @staticmethod
    def _face_points(mn: tuple[float, float, float], mx: tuple[float, float, float], face_idx: int) -> tuple[list[tuple[float, float, float]], tuple[float, float, float]]:
        mnx, mny, mnz = mn
        mxx, mxy, mxz = mx

        if int(face_idx) == 0:
            return ([(mxx, mny, mnz),(mxx, mxy, mnz),(mxx, mxy, mxz),(mxx, mny, mxz)],(1.0, 0.0, 0.0))
        if int(face_idx) == 1:
            return ([(mnx, mny, mxz),(mnx, mxy, mxz),(mnx, mxy, mnz),(mnx, mny, mnz)],(-1.0, 0.0, 0.0))
        if int(face_idx) == 2:
            return ([(mnx, mxy, mnz),(mxx, mxy, mnz),(mxx, mxy, mxz),(mnx, mxy, mxz)],(0.0, 1.0, 0.0))
        if int(face_idx) == 3:
            return ([(mnx, mny, mxz),(mxx, mny, mxz),(mxx, mny, mnz),(mnx, mny, mnz)],(0.0, -1.0, 0.0))
        if int(face_idx) == 4:
            return ([(mnx, mny, mxz),(mnx, mxy, mxz),(mxx, mxy, mxz),(mxx, mny, mxz)],(0.0, 0.0, 1.0))
        return ([(mxx, mny, mnz),(mxx, mxy, mnz),(mnx, mxy, mnz),(mnx, mny, mnz)],(0.0, 0.0, -1.0))

    def build(self, *, x: int, y: int, z: int, state_str: str, get_state: GetState) -> np.ndarray:
        seen: set[tuple[int, ...]] = set()
        out: list[tuple[float, float, float]] = []

        eps = 0.002

        for face in iter_visible_faces(x=int(x), y=int(y), z=int(z), state_str=str(state_str), get_state=get_state, def_lookup=self.def_lookup):
            pts, normal = self._face_points(face.mn, face.mx, int(face.face_idx))
            ox = float(normal[0]) * eps
            oy = float(normal[1]) * eps
            oz = float(normal[2]) * eps

            pushed = [(px + ox, py + oy, pz + oz) for (px, py, pz) in pts]
            edges = ((pushed[0], pushed[1]),(pushed[1], pushed[2]),(pushed[2], pushed[3]),(pushed[3], pushed[0]))

            for a, b in edges:
                key = self._edge_key(a, b)
                if key in seen:
                    continue
                seen.add(key)
                out.append(a)
                out.append(b)

        if not out:
            return np.zeros((0, 3), dtype=np.float32)

        return np.asarray(out, dtype=np.float32)