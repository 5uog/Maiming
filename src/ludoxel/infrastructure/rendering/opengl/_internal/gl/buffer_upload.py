# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/gl/buffer_upload.py
from __future__ import annotations

import numpy as np

from OpenGL.GL import glBindBuffer, glBufferData, glBufferSubData


def upload_array_buffer(*, target: int, buffer: int, usage: int, data: np.ndarray | None, capacity_bytes: int) -> int:
    nbytes = 0 if data is None else int(data.nbytes)

    glBindBuffer(int(target), int(buffer))

    if nbytes <= 0:
        glBufferData(int(target), 0, None, int(usage))
        glBindBuffer(int(target), 0)
        return 0

    if int(capacity_bytes) > 0 and nbytes <= int(capacity_bytes):
        glBufferSubData(int(target), 0, nbytes, data)
        glBindBuffer(int(target), 0)
        return int(capacity_bytes)

    glBufferData(int(target), nbytes, data, int(usage))
    glBindBuffer(int(target), 0)
    return int(nbytes)


def upload_bytes_buffer(*, target: int, buffer: int, usage: int, data: bytes, capacity_bytes: int) -> int:
    payload = bytes(data)
    nbytes = int(len(payload))

    glBindBuffer(int(target), int(buffer))

    if nbytes <= 0:
        glBufferData(int(target), 0, None, int(usage))
        glBindBuffer(int(target), 0)
        return 0

    if int(capacity_bytes) > 0 and nbytes <= int(capacity_bytes):
        glBufferSubData(int(target), 0, nbytes, payload)
        glBindBuffer(int(target), 0)
        return int(capacity_bytes)

    glBufferData(int(target), nbytes, payload, int(usage))
    glBindBuffer(int(target), 0)
    return int(nbytes)
