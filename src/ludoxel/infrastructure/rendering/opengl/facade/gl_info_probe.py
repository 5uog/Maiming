# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/rendering/opengl/facade/gl_info_probe.py
from __future__ import annotations

from dataclasses import dataclass
import re

from OpenGL.GL import glGetString, glGetIntegerv, GL_VENDOR, GL_RENDERER, GL_VERSION, GL_SHADING_LANGUAGE_VERSION, GL_MAJOR_VERSION, GL_MINOR_VERSION, GL_CONTEXT_PROFILE_MASK, GL_CONTEXT_CORE_PROFILE_BIT, GL_CONTEXT_COMPATIBILITY_PROFILE_BIT

_VERSION_RE = re.compile(r"(\d+)\.(\d+)")


@dataclass(frozen=True)
class GLInfoSnapshot:
    vendor: str
    renderer: str
    version: str
    glsl_version: str

    major_version: int
    minor_version: int

    glsl_major_version: int
    glsl_minor_version: int

    context_profile_mask: int

    def is_version_at_least(self, major: int, minor: int) -> bool:
        cur = (int(self.major_version), int(self.minor_version))
        req = (int(major), int(minor))
        return cur >= req

    def is_glsl_at_least(self, major: int, minor: int) -> bool:
        cur = (int(self.glsl_major_version), int(self.glsl_minor_version))
        req = (int(major), int(minor))
        return cur >= req

    def is_core_profile(self) -> bool:
        mask = int(self.context_profile_mask)
        return bool(mask & int(GL_CONTEXT_CORE_PROFILE_BIT))

    def profile_name(self) -> str:
        mask = int(self.context_profile_mask)

        has_core = bool(mask & int(GL_CONTEXT_CORE_PROFILE_BIT))
        has_compat = bool(mask & int(GL_CONTEXT_COMPATIBILITY_PROFILE_BIT))

        if has_core and (not has_compat):
            return "core"
        if has_compat and (not has_core):
            return "compatibility"
        if mask == 0:
            return "unknown"
        return f"mask=0x{mask:X}"


def _gl_get_string(name: int) -> str:
    try:
        raw = glGetString(int(name))
    except Exception:
        return ""

    if raw is None:
        return ""

    if isinstance(raw, (bytes, bytearray)):
        return raw.decode("utf-8", errors="replace")

    return str(raw)


def _gl_get_int(name: int) -> int | None:
    try:
        raw = glGetIntegerv(int(name))
    except Exception:
        return None

    if raw is None:
        return None

    try:
        if hasattr(raw, "__len__") and (not isinstance(raw, (str, bytes, bytearray))):
            if len(raw) <= 0:
                return None
            return int(raw[0])
        return int(raw)
    except Exception:
        return None


def _parse_version_pair(raw: str) -> tuple[int, int]:
    s = str(raw)
    m = _VERSION_RE.search(s)
    if m is None:
        return (0, 0)
    try:
        return (int(m.group(1)), int(m.group(2)))
    except Exception:
        return (0, 0)


def probe_gl_info() -> GLInfoSnapshot:
    version = _gl_get_string(GL_VERSION)
    glsl_version = _gl_get_string(GL_SHADING_LANGUAGE_VERSION)

    major = _gl_get_int(GL_MAJOR_VERSION)
    minor = _gl_get_int(GL_MINOR_VERSION)

    if major is None or minor is None or int(major) < 0 or int(minor) < 0:
        major, minor = _parse_version_pair(version)
    elif int(major) == 0 and int(minor) == 0:
        major, minor = _parse_version_pair(version)

    glsl_major, glsl_minor = _parse_version_pair(glsl_version)

    profile_mask = _gl_get_int(GL_CONTEXT_PROFILE_MASK)
    if profile_mask is None:
        profile_mask = 0

    return GLInfoSnapshot(vendor=_gl_get_string(GL_VENDOR), renderer=_gl_get_string(GL_RENDERER), version=str(version), glsl_version=str(glsl_version), major_version=int(major), minor_version=int(minor), glsl_major_version=int(glsl_major), glsl_minor_version=int(glsl_minor), context_profile_mask=int(profile_mask))
