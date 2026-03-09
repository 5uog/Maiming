# FILE: src/maiming/core/grid/face_index.py
from __future__ import annotations

def face_neighbor_offset(face_idx: int) -> tuple[int, int, int]:
    fi = int(face_idx)

    if fi == 0:
        return (1, 0, 0)
    if fi == 1:
        return (-1, 0, 0)
    if fi == 2:
        return (0, 1, 0)
    if fi == 3:
        return (0, -1, 0)
    if fi == 4:
        return (0, 0, 1)
    return (0, 0, -1)