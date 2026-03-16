# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/gl/instanced_mesh_common.py
from __future__ import annotations

from ctypes import c_void_p

import numpy as np

from OpenGL.GL import GL_ARRAY_BUFFER, GL_FLOAT, GL_STATIC_DRAW, GL_STREAM_DRAW, glBindBuffer, glBindVertexArray, glBufferData, glDeleteBuffers, glDeleteVertexArrays, glEnableVertexAttribArray, glGenBuffers, glGenVertexArrays, glVertexAttribDivisor, glVertexAttribPointer

from .array_view import as_float32_c_array, as_float32_rows
from .buffer_upload import upload_array_buffer


def enable_vertex_attr(location: int, size: int, stride_bytes: int, offset_bytes: int, *, divisor: int=0) -> None:
    glEnableVertexAttribArray(int(location))
    glVertexAttribPointer(int(location), int(size), GL_FLOAT, False, int(stride_bytes), c_void_p(int(offset_bytes)))
    if int(divisor) != 0:
        glVertexAttribDivisor(int(location), int(divisor))


def create_static_vertex_buffer(*, vertices: np.ndarray, cols: int, label: str, attrs: tuple[tuple[int, int, int], ...]) -> tuple[int, int, int]:
    rows = as_float32_rows(vertices, cols=int(cols), label=str(label))
    vao = int(glGenVertexArrays(1))
    glBindVertexArray(int(vao))
    vbo = int(glGenBuffers(1))
    glBindBuffer(GL_ARRAY_BUFFER, int(vbo))
    glBufferData(GL_ARRAY_BUFFER, int(rows.nbytes), rows, GL_STATIC_DRAW)

    stride = int(cols) * 4
    for location, size, offset in attrs:
        enable_vertex_attr(int(location), int(size), int(stride), int(offset))
    return (int(vao), int(vbo), int(rows.shape[0]))


def attach_instance_buffer(*, stride_bytes: int, attrs: tuple[tuple[int, int, int], ...]) -> int:
    instance_vbo = int(glGenBuffers(1))
    glBindBuffer(GL_ARRAY_BUFFER, int(instance_vbo))
    glBufferData(GL_ARRAY_BUFFER, 0, None, GL_STREAM_DRAW)
    for location, size, offset in attrs:
        enable_vertex_attr(int(location), int(size), int(stride_bytes), int(offset), divisor=1)
    return int(instance_vbo)


def upload_instance_rows(*, buffer: int, instance_data: np.ndarray, capacity_bytes: int) -> int:
    data = as_float32_c_array(instance_data)
    return upload_array_buffer(target=GL_ARRAY_BUFFER, buffer=int(buffer), usage=GL_STREAM_DRAW, data=data, capacity_bytes=int(capacity_bytes))


def destroy_mesh_handles(*, vao: int, buffers: tuple[int, ...]) -> None:
    for buffer in buffers:
        glDeleteBuffers(1, [int(buffer)])
    glDeleteVertexArrays(1, [int(vao)])
    glBindVertexArray(0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
