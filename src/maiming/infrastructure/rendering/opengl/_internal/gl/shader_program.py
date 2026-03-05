# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/shader_program.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from OpenGL.GL import (
    glCreateProgram,
    glCreateShader,
    glShaderSource,
    glCompileShader,
    glGetShaderiv,
    glGetShaderInfoLog,
    glAttachShader,
    glLinkProgram,
    glGetProgramiv,
    glGetProgramInfoLog,
    glDeleteShader,
    glUseProgram,
    glGetUniformLocation,
    glUniformMatrix4fv,
    glUniform3f,
    glUniform2f,
    glUniform1i,
    glUniform1f,
    glUniform3i,
    glUniform4f,
    glDeleteProgram,
    GL_VERTEX_SHADER,
    GL_FRAGMENT_SHADER,
    GL_COMPILE_STATUS,
    GL_LINK_STATUS,
)

def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _compile(shader_type: int, src: str) -> int:
    sid = glCreateShader(shader_type)
    glShaderSource(sid, src)
    glCompileShader(sid)
    ok = glGetShaderiv(sid, GL_COMPILE_STATUS)
    if not ok:
        log = glGetShaderInfoLog(sid).decode("utf-8", errors="replace")
        raise RuntimeError(f"Shader compile failed:\n{log}")
    return sid

@dataclass
class ShaderProgram:
    program: int

    @staticmethod
    def from_files(vert_path: Path, frag_path: Path) -> "ShaderProgram":
        vs = _compile(GL_VERTEX_SHADER, _load_text(vert_path))
        fs = _compile(GL_FRAGMENT_SHADER, _load_text(frag_path))

        pid = glCreateProgram()
        glAttachShader(pid, vs)
        glAttachShader(pid, fs)
        glLinkProgram(pid)

        ok = glGetProgramiv(pid, GL_LINK_STATUS)
        if not ok:
            log = glGetProgramInfoLog(pid).decode("utf-8", errors="replace")
            raise RuntimeError(f"Program link failed:\n{log}")

        glDeleteShader(vs)
        glDeleteShader(fs)
        return ShaderProgram(program=pid)

    def destroy(self) -> None:
        if int(self.program) != 0:
            glDeleteProgram(int(self.program))
            self.program = 0

    def use(self) -> None:
        glUseProgram(self.program)

    def uniform_loc(self, name: str) -> int:
        return glGetUniformLocation(self.program, name)

    def set_mat4(self, name: str, m: np.ndarray) -> None:
        loc = self.uniform_loc(name)
        glUniformMatrix4fv(loc, 1, True, m.astype(np.float32))

    def set_vec3(self, name: str, x: float, y: float, z: float) -> None:
        loc = self.uniform_loc(name)
        glUniform3f(loc, float(x), float(y), float(z))

    def set_vec2(self, name: str, x: float, y: float) -> None:
        loc = self.uniform_loc(name)
        glUniform2f(loc, float(x), float(y))

    def set_vec4(self, name: str, x: float, y: float, z: float, w: float) -> None:
        loc = self.uniform_loc(name)
        glUniform4f(loc, float(x), float(y), float(z), float(w))

    def set_int(self, name: str, v: int) -> None:
        loc = self.uniform_loc(name)
        glUniform1i(loc, int(v))

    def set_ivec3(self, name: str, x: int, y: int, z: int) -> None:
        loc = self.uniform_loc(name)
        glUniform3i(loc, int(x), int(y), int(z))

    def set_float(self, name: str, v: float) -> None:
        loc = self.uniform_loc(name)
        glUniform1f(loc, float(v))