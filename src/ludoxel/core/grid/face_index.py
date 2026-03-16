# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/grid/face_index.py
from __future__ import annotations

FACE_POS_X: int = 0
FACE_NEG_X: int = 1
FACE_POS_Y: int = 2
FACE_NEG_Y: int = 3
FACE_POS_Z: int = 4
FACE_NEG_Z: int = 5


def face_neighbor_offset(face_idx: int) -> tuple[int, int, int]:
    """
    offset(fi) =
        ( 1,  0,  0),  if fi == FACE_POS_X,
        (-1,  0,  0),  if fi == FACE_NEG_X,
        ( 0,  1,  0),  if fi == FACE_POS_Y,
        ( 0, -1,  0),  if fi == FACE_NEG_Y,
        ( 0,  0,  1),  if fi == FACE_POS_Z,
        ( 0,  0, -1),  otherwise.

    I convert a face index into the integer offset of the face-adjacent voxel. The implementation is
    a literal case split over the six canonical face constants, with a terminal default branch that
    returns `(0, 0, -1)` for every value not matched earlier. I do not reject invalid indices, and I
    do not return a neutral offset for them.

    This default matters operationally. Any caller that passes a non-canonical face index receives
    the negative-Z neighbor as a fallback artifact of the final return statement, not a validated
    error path.

    I use this mapping in `build_system.py` to derive the candidate placement cell from a picked
    block face, and I also use it in renderer-side face analysis such as `face_occlusion.py` and
    `visible_faces.py` when I query the neighbor across a boundary face.
    """
    fi = int(face_idx)

    if fi == FACE_POS_X:
        return (1, 0, 0)
    if fi == FACE_NEG_X:
        return (-1, 0, 0)
    if fi == FACE_POS_Y:
        return (0, 1, 0)
    if fi == FACE_NEG_Y:
        return (0, -1, 0)
    if fi == FACE_POS_Z:
        return (0, 0, 1)
    return (0, 0, -1)
