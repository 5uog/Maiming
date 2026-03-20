# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
from dataclasses import dataclass

from ....core.math.vec3 import Vec3
from .cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction
from .gl_renderer_params import CloudParams

@dataclass(frozen=True)
class CloudBox:
    center: Vec3
    size: Vec3
    alpha_mul: float

@dataclass(frozen=True)
class _RectXZ:
    min_x: int
    max_x: int
    min_z: int
    max_z: int

class CloudField:
    def __init__(self, cfg: CloudParams) -> None:
        self._cfg = cfg

        self._enabled_density: int = int(max(0, int(cfg.rects_per_cell)))
        self._seed: int = int(cfg.seed)

        self._flow_direction: str = normalize_cloud_flow_direction(DEFAULT_CLOUD_FLOW_DIRECTION)
        self._flow_epoch_s: float = 0.0
        self._flow_base_shift: Vec3 = Vec3(0.0, 0.0, 0.0)

        self._anchor_key: tuple[int, int] | None = None
        self._boxes_cache: list[CloudBox] = []

    def set_density(self, density: int) -> None:
        d = int(max(0, density))
        if d == int(self._enabled_density):
            return
        self._enabled_density = d
        self._anchor_key = None
        self._boxes_cache = []

    def set_seed(self, seed: int) -> None:
        s = int(seed)
        if s == int(self._seed):
            return
        self._seed = s
        self._anchor_key = None
        self._boxes_cache = []

    def set_flow_direction(self, direction: str, *, t_seconds: float = 0.0) -> None:
        nxt = normalize_cloud_flow_direction(str(direction))
        ts = float(max(0.0, t_seconds))

        cur = self.shift(ts)

        self._flow_direction = str(nxt)
        self._flow_epoch_s = float(ts)
        self._flow_base_shift = Vec3(float(cur.x), 0.0, float(cur.z))

    def _flow_speed(self) -> float:
        sx = abs(float(self._cfg.speed_x))
        sz = abs(float(self._cfg.speed_z))
        sp = math.hypot(sx, sz)
        if sp > 1e-9:
            return float(sp)
        return float(max(sx, sz, 0.0))

    def _flow_velocity(self, direction: str) -> tuple[float, float]:
        sp = float(self._flow_speed())
        d = normalize_cloud_flow_direction(str(direction))

        if d == "east_to_west":
            return (-sp, 0.0)
        if d == "west_to_east":
            return (sp, 0.0)
        if d == "south_to_north":
            return (0.0, -sp)
        return (0.0, sp)

    def shift(self, t_seconds: float) -> Vec3:
        ts = float(max(0.0, t_seconds))
        dt = float(max(0.0, ts - float(self._flow_epoch_s)))

        vx, vz = self._flow_velocity(self._flow_direction)
        return Vec3(float(self._flow_base_shift.x) + vx * dt, 0.0, float(self._flow_base_shift.z) + vz * dt)

    def ensure_cache(self, eye: Vec3, shift: Vec3) -> None:
        if int(self._enabled_density) <= 0:
            self._anchor_key = None
            self._boxes_cache = []
            return

        px = float(eye.x) - float(shift.x)
        pz = float(eye.z) - float(shift.z)

        m = int(self._cfg.macro)
        ax = self._floor_div(int(math.floor(px)), m)
        az = self._floor_div(int(math.floor(pz)), m)
        key = (ax, az)

        if self._anchor_key == key:
            return

        self._anchor_key = key
        self._boxes_cache = self._build_cloud_boxes(anchor_mx=ax, anchor_mz=az)

    def visible_boxes(self, eye: Vec3, shift: Vec3, forward: Vec3, fov_deg: float, aspect: float, z_far: float) -> list[CloudBox]:
        self.ensure_cache(eye=eye, shift=shift)

        if not self._boxes_cache:
            return []

        up_hint = Vec3(0.0, 1.0, 0.0)
        right = up_hint.cross(forward).normalized()
        up = forward.cross(right).normalized()

        tan_y = math.tan(math.radians(float(fov_deg)) * 0.5)
        tan_x = tan_y * max(float(aspect), 1e-6)

        out: list[CloudBox] = []
        for b in self._boxes_cache:
            c_world = Vec3(b.center.x + shift.x, b.center.y, b.center.z + shift.z)

            hx = b.size.x * 0.5
            hy = b.size.y * 0.5
            hz = b.size.z * 0.5
            r = math.sqrt(hx * hx + hy * hy + hz * hz)

            v = c_world - eye
            z = v.dot(forward)

            if z <= 0.0:
                continue
            if z - r > float(z_far):
                continue

            x = v.dot(right)
            y = v.dot(up)

            if abs(x) > (z * tan_x + r):
                continue
            if abs(y) > (z * tan_y + r):
                continue

            out.append(b)

        return out

    def _build_cloud_boxes(self, anchor_mx: int, anchor_mz: int) -> list[CloudBox]:
        m = int(self._cfg.macro)
        r = int(self._cfg.view_radius)

        span = int(math.ceil(float(r) / float(m))) + 1

        size_y = float(max(1, int(self._cfg.thickness)))

        rects_per_cell = int(max(0, int(self._enabled_density)))
        if rects_per_cell <= 0:
            return []

        candidates_per_cell = int(max(rects_per_cell, int(self._cfg.candidates_per_cell)))

        boxes: list[CloudBox] = []
        for mx in range(anchor_mx - span, anchor_mx + span + 1):
            for mz in range(anchor_mz - span, anchor_mz + span + 1):
                accepted: list[_RectXZ] = []

                for i in range(candidates_per_cell):
                    r_keep = self._hash3(mx, mz, i, int(self._seed) ^ 0x51ED270B)
                    if r_keep < float(self._cfg.candidate_drop_threshold):
                        continue

                    cx, cz, sx, sz = self._rect_params(mx, mz, i, m)

                    min_x = mx * m + (cx - sx)
                    max_x = mx * m + (cx + sx + 1)
                    min_z = mz * m + (cz - sz)
                    max_z = mz * m + (cz + sz + 1)

                    rect = _RectXZ(min_x=min_x, max_x=max_x, min_z=min_z, max_z=max_z)

                    if self._overlaps_too_much(rect, accepted, thresh=float(self._cfg.overlap_thresh)):
                        continue

                    accepted.append(rect)
                    if len(accepted) >= rects_per_cell:
                        break

                for ridx, rect in enumerate(accepted):
                    size_x = float(rect.max_x - rect.min_x)
                    size_z = float(rect.max_z - rect.min_z)
                    bx = float(rect.min_x) + size_x * 0.5
                    bz = float(rect.min_z) + size_z * 0.5

                    lane_r = self._hash3(mx, mz, ridx, int(self._seed) ^ 0xA24BAEDB)
                    lanes = self._cfg.lane_offsets
                    lane = lanes[0] if lane_r < 0.33 else (lanes[1] if lane_r < 0.66 else lanes[2])

                    y0 = float(int(self._cfg.y) + int(lane))
                    cy = y0 + size_y * 0.5

                    a = float(self._cfg.alpha_min) + float(self._cfg.alpha_range) * self._hash3(mx, mz, ridx, int(self._seed) ^ 0xB5297A4D)

                    boxes.append(CloudBox(center=Vec3(bx, cy, bz), size=Vec3(size_x, size_y, size_z), alpha_mul=float(a)))

        return boxes

    def _rect_params(self, mx: int, mz: int, idx: int, m: int) -> tuple[int, int, int, int]:
        s = int(self._seed) ^ (idx * 0x9E3779B9)

        r1 = self._hash2(mx, mz, s ^ 0xD1B54A35)
        r2 = self._hash2(mx, mz, s ^ 0x94D049BB)
        r3 = self._hash2(mx, mz, s ^ 0xDEADBEEF)
        r4 = self._hash2(mx, mz, s ^ 0xBADC0FFE)

        margin = int(self._cfg.rect_margin)
        usable = max(1, m - 2 * margin)
        cx = margin + int(r1 * float(usable))
        cz = margin + int(r2 * float(usable))

        sx = int(self._cfg.rect_size_min) + int(r3 * float(self._cfg.rect_size_range))
        sz = int(self._cfg.rect_size_min) + int(r4 * float(self._cfg.rect_size_range))

        if m >= 6:
            sx = min(sx, m // 2 - 1)
            sz = min(sz, m // 2 - 1)

        return (cx, cz, sx, sz)

    @staticmethod
    def _overlaps_too_much(r: _RectXZ, prev: list[_RectXZ], thresh: float) -> bool:
        ax0, ax1, az0, az1 = r.min_x, r.max_x, r.min_z, r.max_z
        a_area = max(0, ax1 - ax0) * max(0, az1 - az0)
        if a_area <= 0:
            return True

        for p in prev:
            bx0, bx1, bz0, bz1 = p.min_x, p.max_x, p.min_z, p.max_z
            ix0 = max(ax0, bx0)
            ix1 = min(ax1, bx1)
            iz0 = max(az0, bz0)
            iz1 = min(az1, bz1)
            inter = max(0, ix1 - ix0) * max(0, iz1 - iz0)
            if inter <= 0:
                continue

            b_area = max(0, bx1 - bx0) * max(0, bz1 - bz0)
            denom = float(min(a_area, b_area)) if b_area > 0 else float(a_area)
            if denom > 0 and (float(inter) / denom) > thresh:
                return True

        return False

    @staticmethod
    def _floor_div(a: int, b: int) -> int:
        return a // b

    @staticmethod
    def _hash_u32(n: int) -> int:
        n &= 0xFFFFFFFF
        n ^= (n >> 16) & 0xFFFFFFFF
        n = (n * 0x7FEB352D) & 0xFFFFFFFF
        n ^= (n >> 15) & 0xFFFFFFFF
        n = (n * 0x846CA68B) & 0xFFFFFFFF
        n ^= (n >> 16) & 0xFFFFFFFF
        return n & 0xFFFFFFFF

    def _hash2(self, x: int, z: int, seed: int) -> float:
        n = (x * 374761393) ^ (z * 668265263) ^ (seed * 1442695041)
        u = self._hash_u32(n)
        return float(u) / 4294967295.0

    def _hash3(self, x: int, z: int, y: int, seed: int) -> float:
        n = (x * 374761393) ^ (z * 668265263) ^ (y * 2246822519) ^ (seed * 3266489917)
        u = self._hash_u32(n)
        return float(u) / 4294967295.0