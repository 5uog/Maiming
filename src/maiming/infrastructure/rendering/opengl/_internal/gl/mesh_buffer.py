# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/mesh_buffer.py
from __future__ import annotations

from dataclasses import dataclass
from ctypes import c_void_p
import numpy as np

from OpenGL.GL import (
    glGenVertexArrays, glBindVertexArray, glGenBuffers, glBindBuffer, glBufferData,
    glBufferSubData, glEnableVertexAttribArray, glVertexAttribPointer, glVertexAttribDivisor,
    glDeleteBuffers, glDeleteVertexArrays, GL_ARRAY_BUFFER, GL_STATIC_DRAW, GL_STREAM_DRAW, GL_FLOAT,
)

@dataclass
class MeshBuffer:
    vao: int
    vbo: int
    vertex_count: int
    instance_vbo: int
    instance_capacity: int = 0

    @staticmethod
    def create_cube_instanced() -> "MeshBuffer":
        v = np.array(_cube_vertices(), dtype=np.float32)
        if not v.flags["C_CONTIGUOUS"]:
            v = np.ascontiguousarray(v, dtype=np.float32)

        vertex_count = int(v.shape[0])

        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, v.nbytes, v, GL_STATIC_DRAW)

        stride = 8 * 4

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, c_void_p(0))

        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, False, stride, c_void_p(12))

        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, False, stride, c_void_p(24))

        instance_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_STREAM_DRAW)

        inst_stride = 7 * 4

        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 3, GL_FLOAT, False, inst_stride, c_void_p(0))
        glVertexAttribDivisor(3, 1)

        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 4, GL_FLOAT, False, inst_stride, c_void_p(12))
        glVertexAttribDivisor(4, 1)

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(
            vao=int(vao),
            vbo=int(vbo),
            vertex_count=int(vertex_count),
            instance_vbo=int(instance_vbo),
            instance_capacity=0,
        )

    @staticmethod
    def create_quad_instanced(face: int) -> "MeshBuffer":
        v = np.array(_quad_vertices(face), dtype=np.float32)
        if not v.flags["C_CONTIGUOUS"]:
            v = np.ascontiguousarray(v, dtype=np.float32)

        vertex_count = int(v.shape[0])

        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, v.nbytes, v, GL_STATIC_DRAW)

        stride = 8 * 4

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, c_void_p(0))

        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, False, stride, c_void_p(12))

        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, False, stride, c_void_p(24))

        instance_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)
        glBufferData(GL_ARRAY_BUFFER, 0, None, GL_STREAM_DRAW)

        inst_stride = 12 * 4

        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 3, GL_FLOAT, False, inst_stride, c_void_p(0))
        glVertexAttribDivisor(3, 1)

        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 3, GL_FLOAT, False, inst_stride, c_void_p(12))
        glVertexAttribDivisor(4, 1)

        glEnableVertexAttribArray(5)
        glVertexAttribPointer(5, 4, GL_FLOAT, False, inst_stride, c_void_p(24))
        glVertexAttribDivisor(5, 1)

        glEnableVertexAttribArray(6)
        glVertexAttribPointer(6, 1, GL_FLOAT, False, inst_stride, c_void_p(40))
        glVertexAttribDivisor(6, 1)

        glEnableVertexAttribArray(7)
        glVertexAttribPointer(7, 1, GL_FLOAT, False, inst_stride, c_void_p(44))
        glVertexAttribDivisor(7, 1)

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(
            vao=int(vao),
            vbo=int(vbo),
            vertex_count=int(vertex_count),
            instance_vbo=int(instance_vbo),
            instance_capacity=0,
        )

    def upload_instances(self, instance_data: np.ndarray) -> None:
        if instance_data.dtype != np.float32:
            instance_data = instance_data.astype(np.float32, copy=False)
        if not instance_data.flags["C_CONTIGUOUS"]:
            instance_data = np.ascontiguousarray(instance_data, dtype=np.float32)

        nbytes = int(instance_data.nbytes)

        glBindBuffer(GL_ARRAY_BUFFER, int(self.instance_vbo))

        if nbytes <= 0:
            glBufferData(GL_ARRAY_BUFFER, 0, None, GL_STREAM_DRAW)
            self.instance_capacity = 0
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            return

        cap = int(self.instance_capacity)
        if cap > 0 and nbytes <= cap:
            glBufferSubData(GL_ARRAY_BUFFER, 0, nbytes, instance_data)
        else:
            glBufferData(GL_ARRAY_BUFFER, nbytes, instance_data, GL_STREAM_DRAW)
            self.instance_capacity = nbytes

        glBindBuffer(GL_ARRAY_BUFFER, 0)

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
    return [
        (*a, nx, ny, nz, 0.0, 0.0),
        (*b, nx, ny, nz, 1.0, 0.0),
        (*c, nx, ny, nz, 1.0, 1.0),
        (*a, nx, ny, nz, 0.0, 0.0),
        (*c, nx, ny, nz, 1.0, 1.0),
        (*d, nx, ny, nz, 0.0, 1.0),
    ]

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