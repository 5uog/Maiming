# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/gl/storage_buffer.py
from __future__ import annotations

import numpy as np

from OpenGL.GL import glGenBuffers, glDeleteBuffers, glBindBuffer, glBindBufferBase, glBufferData, glGetBufferSubData, GL_SHADER_STORAGE_BUFFER, GL_DYNAMIC_DRAW

from .buffer_upload import upload_array_buffer, upload_bytes_buffer


class StorageBuffer:

    def __init__(self, *, target: int=GL_SHADER_STORAGE_BUFFER, usage: int=GL_DYNAMIC_DRAW) -> None:
        self._target = int(target)
        self._usage = int(usage)
        self.buffer = int(glGenBuffers(1))
        self.capacity_bytes = 0

    def destroy(self) -> None:
        if int(self.buffer) != 0:
            glDeleteBuffers(1,[int(self.buffer)])
            self.buffer = 0
            self.capacity_bytes = 0

    def ensure_capacity(self, nbytes: int) -> None:
        size = int(max(0, int(nbytes)))
        glBindBuffer(self._target, int(self.buffer))
        if size > int(self.capacity_bytes):
            glBufferData(self._target, size, None, self._usage)
            self.capacity_bytes = int(size)
        elif size == 0 and int(self.capacity_bytes) == 0:
            glBufferData(self._target, 0, None, self._usage)
        glBindBuffer(self._target, 0)

    def set_size(self, nbytes: int) -> None:
        size = int(max(0, int(nbytes)))
        glBindBuffer(self._target, int(self.buffer))
        glBufferData(self._target, size, None, self._usage)
        self.capacity_bytes = int(size)
        glBindBuffer(self._target, 0)

    def upload_bytes(self, data: bytes) -> None:
        self.capacity_bytes = upload_bytes_buffer(target=self._target, buffer=int(self.buffer), usage=self._usage, data=bytes(data), capacity_bytes=int(self.capacity_bytes))

    def upload_array(self, data: np.ndarray) -> None:
        arr = data
        if not arr.flags["C_CONTIGUOUS"]:
            arr = np.ascontiguousarray(arr)
        self.capacity_bytes = upload_array_buffer(target=self._target, buffer=int(self.buffer), usage=self._usage, data=arr, capacity_bytes=int(self.capacity_bytes))

    def bind_base(self, index: int) -> None:
        glBindBufferBase(self._target, int(index), int(self.buffer))

    def unbind_base(self, index: int) -> None:
        glBindBufferBase(self._target, int(index), 0)

    def read_bytes(self, nbytes: int) -> bytes:
        size = int(max(0, int(nbytes)))
        if size <= 0:
            return b""

        glBindBuffer(self._target, int(self.buffer))
        raw = glGetBufferSubData(self._target, 0, size)
        glBindBuffer(self._target, 0)

        if isinstance(raw,(bytes, bytearray)):
            return bytes(raw)
        return bytes(raw)
