# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = ["GLRenderer", "CameraParams", "ShadowParams", "SunParams", "CloudParams", "SkyParams", "GLRendererParams", "default_gl_renderer_params", "GLResources", "build_chunk_mesh_cpu"]

def __getattr__(name: str):
    if str(name) == "GLRenderer":
        from ludoxel.shared.opengl.runtime.gl_renderer import GLRenderer
        return GLRenderer

    if str(name) in {"CameraParams", "ShadowParams", "SunParams", "CloudParams", "SkyParams", "GLRendererParams", "default_gl_renderer_params"}:
        from ludoxel.shared.opengl.runtime.gl_renderer_params import CameraParams, CloudParams, GLRendererParams, ShadowParams, SkyParams, SunParams, default_gl_renderer_params
        mapping = {"CameraParams": CameraParams, "ShadowParams": ShadowParams, "SunParams": SunParams, "CloudParams": CloudParams, "SkyParams": SkyParams, "GLRendererParams": GLRendererParams, "default_gl_renderer_params": default_gl_renderer_params}
        return mapping[str(name)]

    if str(name) == "GLResources":
        from ludoxel.shared.opengl.runtime.gl_resources import GLResources
        return GLResources

    if str(name) == "build_chunk_mesh_cpu":
        from ludoxel.shared.rendering.chunk_face_payload_cpu import build_chunk_mesh_cpu
        return build_chunk_mesh_cpu
    raise AttributeError(str(name))