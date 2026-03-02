# FILE: src/maiming/infrastructure/rendering/opengl/_internal/facade/gl_renderer.py
from __future__ import annotations

import math
import numpy as np
from pathlib import Path

from OpenGL.GL import (
    glClearColor, glClear, glViewport,
    glEnable, glDepthFunc, glDepthMask,
    glGetString,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST, GL_LESS,
    GL_VENDOR, GL_RENDERER, GL_VERSION, GL_SHADING_LANGUAGE_VERSION,
)

from maiming.core.math.vec3 import Vec3
from maiming.core.math import mat4
from maiming.core.math.view_angles import forward_from_yaw_pitch_deg, sun_dir_from_az_el_deg

from maiming.domain.blocks.state_codec import parse_state
from maiming.domain.blocks.block_definition import BlockDefinition
from maiming.domain.world.chunking import chunk_key

from .gl_renderer_params import GLRendererParams, default_gl_renderer_params
from .gl_resources import GLResources
from .._internal.passes.shadow_map_pass import ShadowMapPass
from .._internal.passes.world_pass import WorldPass, WorldDrawInputs
from .._internal.passes.sun_pass import SunPass
from .._internal.passes.cloud_pass import CloudPass
from .._internal.pipeline.light_space import compute_light_view_proj
from maiming.domain.world.chunking import ChunkKey

class GLRenderer:
    def __init__(self, params: GLRendererParams | None = None) -> None:
        self._cfg = params or default_gl_renderer_params()

        self._res: GLResources | None = None

        self._sun_azimuth_deg = float(self._cfg.sun.azimuth_deg)
        self._sun_elevation_deg = float(self._cfg.sun.elevation_deg)
        self._sun_dir = sun_dir_from_az_el_deg(self._sun_azimuth_deg, self._sun_elevation_deg)

        self._shadow = ShadowMapPass(self._cfg.shadow)
        self._world = WorldPass()
        self._sun = SunPass(self._cfg.sun)
        self._cloud = CloudPass(self._cfg.clouds, self._cfg.camera)

        self._debug_shadow = False
        self._shadow_enabled = True
        self._world_wireframe = False

        self._gl_vendor: str = ""
        self._gl_renderer: str = ""
        self._gl_version: str = ""
        self._glsl_version: str = ""

    def initialize(self, assets_dir: Path) -> None:
        self._res = GLResources.load(assets_dir)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        self._shadow.initialize(self._res.shadow_prog, int(self._cfg.shadow.size))
        self._world.initialize(self._res.world_prog, self._res.atlas)
        self._sun.initialize(self._res.sun_prog, int(self._res.empty_vao))
        self._cloud.initialize(self._res.cloud_prog, self._res.cloud_mesh)

        self._gl_vendor = self._gl_get_string(GL_VENDOR)
        self._gl_renderer = self._gl_get_string(GL_RENDERER)
        self._gl_version = self._gl_get_string(GL_VERSION)
        self._glsl_version = self._gl_get_string(GL_SHADING_LANGUAGE_VERSION)

    @staticmethod
    def _gl_get_string(name: int) -> str:
        try:
            v = glGetString(int(name))
            if v is None:
                return ""
            if isinstance(v, (bytes, bytearray)):
                return v.decode("utf-8", errors="replace")
            return str(v)
        except Exception:
            return ""

    def gl_info(self) -> tuple[str, str, str, str]:
        return (str(self._gl_vendor), str(self._gl_renderer), str(self._gl_version), str(self._glsl_version))

    def set_cloud_wireframe(self, on: bool) -> None:
        self._cloud.set_wireframe(bool(on))

    def set_cloud_enabled(self, on: bool) -> None:
        self._cloud.set_enabled(bool(on))

    def set_cloud_density(self, density: int) -> None:
        self._cloud.set_density(int(density))

    def set_cloud_seed(self, seed: int) -> None:
        self._cloud.set_seed(int(seed))

    def set_world_wireframe(self, on: bool) -> None:
        self._world_wireframe = bool(on)

    def set_shadow_enabled(self, on: bool) -> None:
        self._shadow_enabled = bool(on)

    def set_debug_shadow(self, on: bool) -> None:
        self._debug_shadow = bool(on)

    def sun_angles(self) -> tuple[float, float]:
        return (float(self._sun_azimuth_deg), float(self._sun_elevation_deg))

    def set_sun_angles(self, azimuth_deg: float, elevation_deg: float) -> None:
        az = float(azimuth_deg) % 360.0
        if az < 0.0:
            az += 360.0
        el = float(elevation_deg)
        el = max(0.0, min(90.0, el))

        self._sun_azimuth_deg = az
        self._sun_elevation_deg = el
        self._sun_dir = sun_dir_from_az_el_deg(self._sun_azimuth_deg, self._sun_elevation_deg)

    def sun_dir(self) -> Vec3:
        return self._sun_dir

    def shadow_info(self) -> tuple[bool, int]:
        if not bool(self._shadow_enabled):
            return (False, 0)

        info = self._shadow.info()
        ok = bool(self._cfg.shadow.enabled and info.ok and info.tex_id != 0 and info.inst_count > 0)
        return (ok, int(info.size) if ok else 0)

    def shadow_status_text(self) -> str:
        ok, _ = self.shadow_info()
        return "SHADOWMAP_ON" if ok else "SHADOWMAP_OFF"

    def atlas_uv_face(self, block_state_id: str, face_idx: int) -> tuple[float, float, float, float]:
        if self._res is None:
            return (0.0, 0.0, 1.0, 1.0)

        base_id, _p = parse_state(str(block_state_id))
        b = self._res.blocks.get(str(base_id))
        tex_name = b.texture_for_face(int(face_idx)) if b is not None else "default"

        uv = self._res.atlas.uv.get(str(tex_name))
        if uv is None:
            uv = self._res.atlas.uv.get("default", (0.0, 0.0, 1.0, 1.0))
        return (float(uv[0]), float(uv[1]), float(uv[2]), float(uv[3]))

    def world_build_tools(self):
        if self._res is None:
            return None

        def def_lookup(base_id: str) -> BlockDefinition | None:
            return self._res.blocks.get(str(base_id))

        return (self.atlas_uv_face, def_lookup)

    def block_display_name(self, block_state_or_id: str) -> str:
        raw = str(block_state_or_id)
        base, _p = parse_state(raw)
        if self._res is None:
            return str(base)
        d = self._res.blocks.get(str(base))
        return str(d.display_name) if d is not None else str(base)

    def submit_chunk(
        self,
        *,
        chunk_key: ChunkKey,
        world_revision: int,
        faces: list[np.ndarray],
        casters: np.ndarray,
    ) -> None:
        if self._res is None:
            return
        self._world.upload_chunk(chunk_key=chunk_key, world_revision=int(world_revision), faces=faces)
        self._shadow.set_chunk_casters(chunk_key=chunk_key, world_revision=int(world_revision), casters=casters)

    def render(
        self,
        *,
        w: int,
        h: int,
        eye: Vec3,
        yaw_deg: float,
        pitch_deg: float,
        fov_deg: float,
        render_distance_chunks: int,
    ) -> None:
        if self._res is None:
            return

        shadow_info_pre = self._shadow.info()
        light_vp = compute_light_view_proj(
            center=eye,
            sun_dir=self._sun_dir,
            sun=self._cfg.sun,
            shadow=self._cfg.shadow,
            shadow_size=int(max(1, int(shadow_info_pre.size))),
        )

        if bool(self._shadow_enabled) and self._shadow.should_render(light_vp):
            self._shadow.render(light_vp)

        forward = forward_from_yaw_pitch_deg(yaw_deg, pitch_deg)

        view = mat4.look_dir(eye, forward)
        proj = mat4.perspective(fov_deg, (w / max(h, 1)), float(self._cfg.camera.z_near), float(self._cfg.camera.z_far))
        vp = mat4.mul(proj, view)

        glViewport(0, 0, w, h)
        cc = self._cfg.sky.clear_color
        glClearColor(float(cc.x), float(cc.y), float(cc.z), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._sun.draw(eye=eye, view_proj=vp, sun_dir=self._sun_dir)

        glEnable(GL_DEPTH_TEST)
        glDepthMask(True)
        glDepthFunc(GL_LESS)

        shadow_info = self._shadow.info()

        bx = int(math.floor(float(eye.x)))
        by = int(math.floor(float(eye.y)))
        bz = int(math.floor(float(eye.z)))
        cam_ck = chunk_key(bx, by, bz)

        self._world.draw(
            WorldDrawInputs(
                view_proj=vp,
                light_view_proj=light_vp,
                sun_dir=self._sun_dir,
                debug_shadow=bool(self._debug_shadow),
                shadow_enabled=bool(self._shadow_enabled),
                world_wireframe=bool(self._world_wireframe),
                shadow=self._cfg.shadow,
                shadow_info=shadow_info,
                camera_chunk=cam_ck,
                render_distance_chunks=int(render_distance_chunks),
            )
        )

        self._cloud.draw(
            eye=eye,
            view_proj=vp,
            forward=forward,
            fov_deg=float(fov_deg),
            aspect=float(w) / max(float(h), 1.0),
            sun_dir=self._sun_dir,
        )