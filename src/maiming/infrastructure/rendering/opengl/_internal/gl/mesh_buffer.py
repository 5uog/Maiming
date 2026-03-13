# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/mesh_buffer.py
from __future__ import annotations
from ctypes import c_void_p
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import glGenVertexArrays, glGenBuffers, glDeleteBuffers, glDeleteVertexArrays, glBindVertexArray, glBindBuffer, glBufferData, glEnableVertexAttribArray, glVertexAttribPointer, glVertexAttribDivisor, GL_ARRAY_BUFFER, GL_STATIC_DRAW, GL_STREAM_DRAW, GL_FLOAT

from .array_view import as_float32_c_array, as_float32_rows
from .buffer_upload import upload_array_buffer

def _enable_vertex_attr(location: int, size: int, stride_bytes: int, offset_bytes: int, *, divisor: int = 0) -> None:
    glEnableVertexAttribArray(int(location))
    glVertexAttribPointer(int(location), int(size), GL_FLOAT, False, int(stride_bytes), c_void_p(int(offset_bytes)))
    if int(divisor) != 0:
        glVertexAttribDivisor(int(location), int(divisor))

def _create_static_vertex_buffer(vertices: np.ndarray) -> tuple[int, int, int]:
    v = as_float32_rows(vertices, cols=8, label="Static mesh vertices")

    vao = int(glGenVertexArrays(1))
    glBindVertexArray(int(vao))

    vbo = int(glGenBuffers(1))
    glBindBuffer(GL_ARRAY_BUFFER, int(vbo))
    glBufferData(GL_ARRAY_BUFFER, int(v.nbytes), v, GL_STATIC_DRAW)

    stride = 8 * 4
    _enable_vertex_attr(0, 3, stride, 0)
    _enable_vertex_attr(1, 3, stride, 12)
    _enable_vertex_attr(2, 2, stride, 24)

    return int(vao), int(vbo), int(v.shape[0])

def _attach_instance_buffer(*, stride_bytes: int, attrs: tuple[tuple[int, int, int], ...]) -> int:
    instance_vbo = int(glGenBuffers(1))
    glBindBuffer(GL_ARRAY_BUFFER, int(instance_vbo))
    glBufferData(GL_ARRAY_BUFFER, 0, None, GL_STREAM_DRAW)

    for location, size, offset in attrs:
        _enable_vertex_attr(int(location), int(size), int(stride_bytes), int(offset), divisor=1)

    return int(instance_vbo)

@dataclass
class MeshBuffer:
    vao: int
    vbo: int
    vertex_count: int
    instance_vbo: int
    instance_capacity: int = 0

    @staticmethod
    def create_cube_instanced() -> "MeshBuffer":
        vao, vbo, vertex_count = _create_static_vertex_buffer(np.asarray(_cube_vertices(), dtype=np.float32))
        instance_vbo = _attach_instance_buffer(stride_bytes=7 * 4, attrs=((3, 3, 0), (4, 4, 12)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    @staticmethod
    def create_cube_transform_instanced() -> "MeshBuffer":
        vao, vbo, vertex_count = _create_static_vertex_buffer(np.asarray(_cube_vertices(), dtype=np.float32))
        instance_vbo = _attach_instance_buffer(stride_bytes=16 * 4, attrs=((3, 4, 0), (4, 4, 16), (5, 4, 32), (6, 4, 48)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    @staticmethod
    def create_quad_instanced(face: int) -> "MeshBuffer":
        vao, vbo, vertex_count = _create_static_vertex_buffer(np.asarray(_quad_vertices(face), dtype=np.float32))
        instance_vbo = _attach_instance_buffer(stride_bytes=12 * 4, attrs=((3, 3, 0), (4, 3, 12), (5, 4, 24), (6, 1, 40), (7, 1, 44)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

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

def _face(nx, ny, nz, corners):
    (a, b, c, d) = corners
    return [(*a, nx, ny, nz, 0.0, 0.0), (*b, nx, ny, nz, 1.0, 0.0), (*c, nx, ny, nz, 1.0, 1.0), (*a, nx, ny, nz, 0.0, 0.0), (*c, nx, ny, nz, 1.0, 1.0), (*d, nx, ny, nz, 0.0, 1.0)]

def _quad_vertices(face: int):
    p = 0.5

    if face == 0:
        return _face(1, 0, 0, [(p, -p, -p), (p, -p, p), (p, p, p), (p, p, -p)])
    if face == 1:
        return _face(-1, 0, 0, [(-p, -p, p), (-p, -p, -p), (-p, p, -p), (-p, p, p)])
    if face == 2:
        return _face(0, 1, 0, [(-p, p, -p), (p, p, -p), (p, p, p), (-p, p, p)])
    if face == 3:
        return _face(0, -1, 0, [(-p, -p, p), (p, -p, p), (p, -p, -p), (-p, -p, -p)])
    if face == 4:
        return _face(0, 0, 1, [(p, -p, p), (-p, -p, p), (-p, p, p), (p, p, p)])
    return _face(0, 0, -1, [(-p, -p, -p), (p, -p, -p), (p, p, -p), (-p, p, -p)])

def _cube_vertices():
    p = 0.5
    faces = []

    faces.extend(_face(1, 0, 0, [(p, -p, -p), (p, -p, p), (p, p, p), (p, p, -p)]))
    faces.extend(_face(-1, 0, 0, [(-p, -p, p), (-p, -p, -p), (-p, p, -p), (-p, p, p)]))
    faces.extend(_face(0, 1, 0, [(-p, p, -p), (p, p, -p), (p, p, p), (-p, p, p)]))
    faces.extend(_face(0, -1, 0, [(-p, -p, p), (p, -p, p), (p, -p, -p), (-p, -p, -p)]))
    faces.extend(_face(0, 0, 1, [(p, -p, p), (-p, -p, p), (-p, p, p), (p, p, p)]))
    faces.extend(_face(0, 0, -1, [(-p, -p, -p), (p, -p, -p), (p, p, -p), (-p, p, -p)]))

    return faces