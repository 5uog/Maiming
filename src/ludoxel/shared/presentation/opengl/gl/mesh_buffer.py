# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/gl/mesh_buffer.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from OpenGL.GL import GL_ARRAY_BUFFER, glBindBuffer, glBindVertexArray

from .instanced_mesh_common import attach_instance_buffer, create_static_vertex_buffer, destroy_mesh_handles, upload_instance_rows


def _create_default_vertex_buffer(vertices: np.ndarray) -> tuple[int, int, int]:
    return create_static_vertex_buffer(vertices=vertices, cols=8, label="Static mesh vertices", attrs=((0, 3, 0),(1, 3, 12),(2, 2, 24)))


@dataclass
class MeshBuffer:
    vao: int
    vbo: int
    vertex_count: int
    instance_vbo: int
    instance_capacity: int = 0

    @staticmethod
    def create_cube_instanced() -> "MeshBuffer":
        vao, vbo, vertex_count = _create_default_vertex_buffer(np.asarray(_cube_vertices(), dtype=np.float32))
        instance_vbo = attach_instance_buffer(stride_bytes=7 * 4, attrs=((3, 3, 0),(4, 4, 12)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    @staticmethod
    def create_cube_transform_instanced() -> "MeshBuffer":
        vao, vbo, vertex_count = _create_default_vertex_buffer(np.asarray(_cube_vertices(), dtype=np.float32))
        instance_vbo = attach_instance_buffer(stride_bytes=16 * 4, attrs=((3, 4, 0),(4, 4, 16),(5, 4, 32),(6, 4, 48)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    @staticmethod
    def create_quad_instanced(face: int) -> "MeshBuffer":
        vao, vbo, vertex_count = _create_default_vertex_buffer(np.asarray(_quad_vertices(face), dtype=np.float32))
        instance_vbo = attach_instance_buffer(stride_bytes=12 * 4, attrs=((3, 3, 0),(4, 3, 12),(5, 4, 24),(6, 1, 40),(7, 1, 44)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    @staticmethod
    def create_quad_transform_instanced(face: int) -> "MeshBuffer":
        vao, vbo, vertex_count = _create_default_vertex_buffer(np.asarray(_quad_vertices(face), dtype=np.float32))
        instance_vbo = attach_instance_buffer(stride_bytes=20 * 4, attrs=((3, 4, 0),(4, 4, 16),(5, 4, 32),(6, 4, 48),(7, 4, 64)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return MeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    def upload_instances(self, instance_data: np.ndarray) -> None:
        self.instance_capacity = upload_instance_rows(buffer=int(self.instance_vbo), instance_data=instance_data, capacity_bytes=int(self.instance_capacity))

    def destroy(self) -> None:
        destroy_mesh_handles(vao=int(self.vao), buffers=(int(self.vbo), int(self.instance_vbo)))
        self.vbo = 0
        self.instance_vbo = 0
        self.vao = 0
        self.instance_capacity = 0


def _face(nx, ny, nz, corners):
    (a, b, c, d) = corners
    return [(*a, nx, ny, nz, 0.0, 0.0),(*b, nx, ny, nz, 1.0, 0.0),(*c, nx, ny, nz, 1.0, 1.0),(*a, nx, ny, nz, 0.0, 0.0),(*c, nx, ny, nz, 1.0, 1.0),(*d, nx, ny, nz, 0.0, 1.0)]


def _quad_vertices(face: int):
    p = 0.5

    if face == 0:
        return _face(1, 0, 0,[(p, -p, -p),(p, -p, p),(p, p, p),(p, p, -p)])
    if face == 1:
        return _face(-1, 0, 0,[(-p, -p, p),(-p, -p, -p),(-p, p, -p),(-p, p, p)])
    if face == 2:
        return _face(0, 1, 0,[(-p, p, -p),(p, p, -p),(p, p, p),(-p, p, p)])
    if face == 3:
        return _face(0, -1, 0,[(-p, -p, p),(p, -p, p),(p, -p, -p),(-p, -p, -p)])
    if face == 4:
        return _face(0, 0, 1,[(p, -p, p),(-p, -p, p),(-p, p, p),(p, p, p)])
    return _face(0, 0, -1,[(-p, -p, -p),(p, -p, -p),(p, p, -p),(-p, p, -p)])


def _cube_vertices():
    p = 0.5
    faces = []

    faces.extend(_face(1, 0, 0,[(p, -p, -p),(p, -p, p),(p, p, p),(p, p, -p)]))
    faces.extend(_face(-1, 0, 0,[(-p, -p, p),(-p, -p, -p),(-p, p, -p),(-p, p, p)]))
    faces.extend(_face(0, 1, 0,[(-p, p, -p),(p, p, -p),(p, p, p),(-p, p, p)]))
    faces.extend(_face(0, -1, 0,[(-p, -p, p),(p, -p, p),(p, -p, -p),(-p, -p, -p)]))
    faces.extend(_face(0, 0, 1,[(p, -p, p),(-p, -p, p),(-p, p, p),(p, p, p)]))
    faces.extend(_face(0, 0, -1,[(-p, -p, -p),(p, -p, -p),(p, p, -p),(-p, p, -p)]))

    return faces
