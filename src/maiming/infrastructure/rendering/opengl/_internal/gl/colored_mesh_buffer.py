# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/colored_mesh_buffer.py
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from OpenGL.GL import GL_ARRAY_BUFFER, glBindBuffer, glBindVertexArray

from .instanced_mesh_common import attach_instance_buffer, create_static_vertex_buffer, destroy_mesh_handles, upload_instance_rows

@dataclass
class ColoredMeshBuffer:
    vao: int
    vbo: int
    vertex_count: int
    instance_vbo: int
    instance_capacity: int = 0

    @staticmethod
    def create_transform_color_instanced(vertices: np.ndarray) -> "ColoredMeshBuffer":
        vao, vbo, vertex_count = create_static_vertex_buffer(vertices=vertices, cols=9, label="Colored mesh vertices", attrs=((0, 3, 0), (1, 3, 12), (2, 3, 24)))
        instance_vbo = attach_instance_buffer(stride_bytes=20 * 4, attrs=((3, 4, 0), (4, 4, 16), (5, 4, 32), (6, 4, 48), (7, 4, 64)))

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        return ColoredMeshBuffer(vao=int(vao), vbo=int(vbo), vertex_count=int(vertex_count), instance_vbo=int(instance_vbo), instance_capacity=0)

    def upload_instances(self, instance_data: np.ndarray) -> None:
        self.instance_capacity = upload_instance_rows(buffer=int(self.instance_vbo), instance_data=instance_data, capacity_bytes=int(self.instance_capacity))

    def destroy(self) -> None:
        destroy_mesh_handles(vao=int(self.vao), buffers=(int(self.vbo), int(self.instance_vbo)))
        self.vbo = 0
        self.instance_vbo = 0
        self.vao = 0
        self.instance_capacity = 0