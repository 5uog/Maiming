# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/colored_mesh_buffer.py
from __future__ import annotations
from ctypes import c_void_p
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import GL_ARRAY_BUFFER, GL_FLOAT, GL_STATIC_DRAW, GL_STREAM_DRAW, glBindBuffer, glBindVertexArray, glBufferData, glDeleteBuffers, glDeleteVertexArrays, glEnableVertexAttribArray, glGenBuffers, glGenVertexArrays, glVertexAttribDivisor, glVertexAttribPointer

from .array_view import as_float32_c_array, as_float32_rows
from .buffer_upload import upload_array_buffer

def _enable_vertex_attr(location: int, size: int, stride_bytes: int, offset_bytes: int, *, divisor: int = 0) -> None:
    glEnableVertexAttribArray(int(location))
    glVertexAttribPointer(int(location), int(size), GL_FLOAT, False, int(stride_bytes), c_void_p(int(offset_bytes)))
    if int(divisor) != 0:
        glVertexAttribDivisor(int(location), int(divisor))

@dataclass
class ColoredMeshBuffer:
    vao: int
    vbo: int
    vertex_count: int
    instance_vbo: int
    instance_capacity: int = 0

    @staticmethod
    def create_transform_color_instanced(vertices: np.ndarray) -> "ColoredMeshBuffer":
        vertex_rows = as_float32_rows(vertices, cols=9, label="Colored mesh vertices")

        vao = int(glGenVertexArrays(1))
        glBindVertexArray(int(vao))

        vbo = int(glGenBuffers(1))
        glBindBuffer(GL_ARRAY_BUFFER, int(vbo))
        glBufferData(GL_ARRAY_BUFFER, int(vertex_rows.nbytes), vertex_rows, GL_STATIC_DRAW)

        stride = 9 * 4
        _enable_vertex_attr(0, 3, stride, 0)
        _enable_vertex_attr(1, 3, stride, 12)
        _enable_vertex_attr(2, 3, stride, 24)

        instance_vbo = int(glGenBuffers(1))
        glBindBuffer(GL_ARRAY_BUFFER, int(instance_vbo))
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_STREAM_DRAW)

        instance_stride = 20 * 4
        _enable_vertex_attr(3, 4, instance_stride, 0, divisor=1)
        _enable_vertex_attr(4, 4, instance_stride, 16, divisor=1)
        _enable_vertex_attr(5, 4, instance_stride, 32, divisor=1)
        _enable_vertex_attr(6, 4, instance_stride, 48, divisor=1)
        _enable_vertex_attr(7, 4, instance_stride, 64, divisor=1)

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return ColoredMeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_rows.shape[0]), instance_vbo=int(instance_vbo), instance_capacity=0)

    def upload_instances(self, instance_data: np.ndarray) -> None:
        data = as_float32_c_array(instance_data)
        self.instance_capacity = upload_array_buffer(target=GL_ARRAY_BUFFER, buffer=int(self.instance_vbo), usage=GL_STREAM_DRAW, data=data, capacity_bytes=int(self.instance_capacity))

    def destroy(self) -> None:
        glDeleteBuffers(1, [int(self.vbo)])
        glDeleteBuffers(1, [int(self.instance_vbo)])
        glDeleteVertexArrays(1, [int(self.vao)])
        self.vbo = 0
        self.instance_vbo = 0
        self.vao = 0
        self.instance_capacity = 0