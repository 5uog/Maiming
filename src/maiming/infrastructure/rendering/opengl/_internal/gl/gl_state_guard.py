# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/gl_state_guard.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from OpenGL.GL import (
    glGetIntegerv, glIsEnabled, glEnable, glDisable, glBindFramebuffer, glViewport, glCullFace, glPolygonMode,
    GL_FRAMEBUFFER, GL_FRAMEBUFFER_BINDING, GL_VIEWPORT, GL_CULL_FACE_MODE, GL_POLYGON_MODE, GL_FRONT_AND_BACK,
)

@dataclass(frozen=True)
class _EnableCapState:
    cap: int
    enabled: bool

class GLStateGuard:
    def __init__(
        self,
        *,
        capture_framebuffer: bool = True,
        capture_viewport: bool = True,
        capture_enables: Sequence[int] = (),
        capture_cull_mode: bool = False,
        capture_polygon_mode: bool = False,
    ) -> None:
        self._cap_fb = bool(capture_framebuffer)
        self._cap_vp = bool(capture_viewport)
        self._cap_en = tuple(int(x) for x in capture_enables)
        self._cap_cull = bool(capture_cull_mode)
        self._cap_poly = bool(capture_polygon_mode)

        self._prev_fb: int | None = None
        self._prev_vp: tuple[int, int, int, int] | None = None
        self._prev_en: list[_EnableCapState] = []
        self._prev_cull_mode: int | None = None

        # Stored as a single mode restored with GL_FRONT_AND_BACK.
        self._prev_poly_mode: int | None = None

    def __enter__(self) -> "GLStateGuard":
        if self._cap_fb:
            self._prev_fb = int(glGetIntegerv(GL_FRAMEBUFFER_BINDING))

        if self._cap_vp:
            vp = glGetIntegerv(GL_VIEWPORT)
            if vp is not None and len(vp) == 4:
                self._prev_vp = (int(vp[0]), int(vp[1]), int(vp[2]), int(vp[3]))
            else:
                self._prev_vp = None

        if self._cap_en:
            self._prev_en = [_EnableCapState(cap=c, enabled=bool(glIsEnabled(c))) for c in self._cap_en]

        if self._cap_cull:
            self._prev_cull_mode = int(glGetIntegerv(GL_CULL_FACE_MODE))

        if self._cap_poly:
            pm = glGetIntegerv(GL_POLYGON_MODE)
            # GL_POLYGON_MODE typically returns [frontMode, backMode].
            # We restore via GL_FRONT_AND_BACK with a single mode to avoid profile-specific enum issues.
            if pm is None:
                self._prev_poly_mode = None
            elif hasattr(pm, "__len__") and len(pm) >= 1:
                self._prev_poly_mode = int(pm[0])
            else:
                self._prev_poly_mode = int(pm)

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._cap_poly and self._prev_poly_mode is not None:
            glPolygonMode(GL_FRONT_AND_BACK, int(self._prev_poly_mode))

        if self._cap_cull and self._prev_cull_mode is not None:
            glCullFace(int(self._prev_cull_mode))

        if self._prev_en:
            for st in self._prev_en:
                if st.enabled:
                    glEnable(int(st.cap))
                else:
                    glDisable(int(st.cap))

        if self._cap_fb and self._prev_fb is not None:
            glBindFramebuffer(GL_FRAMEBUFFER, int(self._prev_fb))

        if self._cap_vp and self._prev_vp is not None:
            x, y, w, h = self._prev_vp
            glViewport(int(x), int(y), int(w), int(h))