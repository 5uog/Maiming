# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import re
import numpy as np

from OpenGL.GL import glCreateProgram, glCreateShader, glCompileShader, glGetShaderiv, glGetShaderInfoLog, glAttachShader, glLinkProgram, glGetProgramInfoLog, glDeleteShader, glUseProgram, glGetUniformLocation, glUniformMatrix4fv, glUniform3f, glUniform2f, glUniform1i, glUniform1f, glUniform3i, glUniform4f, glDeleteProgram, glShaderSource, glGetProgramiv, GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER, GL_COMPILE_STATUS, GL_LINK_STATUS

_INCLUDE_RE = re.compile(r'^\s*#include\s+"([^"]+)"\s*$')

def _load_text(path: Path) -> str:
    return _load_text_recursive(Path(path).resolve(), stack=())

def _load_text_recursive(path: Path, *, stack: tuple[Path, ...]) -> str:
    p = Path(path).resolve()

    if p in stack:
        chain = " -> ".join(str(x) for x in (*stack, p))
        raise RuntimeError(f"Shader include cycle detected: {chain}")

    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read shader source: {p}") from exc

    next_stack = (*stack, p)
    out_lines: list[str] = []

    for raw_line in raw.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        m = _INCLUDE_RE.match(str(line))
        if m is None:
            out_lines.append(raw_line)
            continue

        include_path = (p.parent / str(m.group(1))).resolve()
        included = _load_text_recursive(include_path, stack=next_stack)
        if included and (not included.endswith("\n")):
            included += "\n"
        out_lines.append(included)

    return "".join(out_lines)

def _shader_stage_name(shader_type: int) -> str:
    st = int(shader_type)
    if st == int(GL_VERTEX_SHADER):
        return "vertex"
    if st == int(GL_FRAGMENT_SHADER):
        return "fragment"
    if st == int(GL_COMPUTE_SHADER):
        return "compute"
    return f"shader({st})"

def _compile(shader_type: int, src: str) -> int:
    sid = glCreateShader(shader_type)
    glShaderSource(sid, src)
    glCompileShader(sid)
    ok = glGetShaderiv(sid, GL_COMPILE_STATUS)
    if not ok:
        log = glGetShaderInfoLog(sid).decode("utf-8", errors="replace")
        stage = _shader_stage_name(int(shader_type))
        raise RuntimeError(f"{stage.capitalize()} shader compile failed:\n{log}")
    return sid

def _link_program(shader_ids: list[int]) -> int:
    pid = glCreateProgram()
    for sid in shader_ids:
        glAttachShader(pid, int(sid))
    glLinkProgram(pid)

    ok = glGetProgramiv(pid, GL_LINK_STATUS)
    if not ok:
        log = glGetProgramInfoLog(pid).decode("utf-8", errors="replace")
        raise RuntimeError(f"Program link failed:\n{log}")

    for sid in shader_ids:
        glDeleteShader(int(sid))

    return int(pid)

@dataclass
class ShaderProgram:
    program: int

    @staticmethod
    def from_files(vert_path: Path, frag_path: Path) -> "ShaderProgram":
        vs = _compile(GL_VERTEX_SHADER, _load_text(vert_path))
        fs = _compile(GL_FRAGMENT_SHADER, _load_text(frag_path))
        pid = _link_program([vs, fs])
        return ShaderProgram(program=int(pid))

    @staticmethod
    def from_compute_file(compute_path: Path) -> "ShaderProgram":
        cs = _compile(GL_COMPUTE_SHADER, _load_text(compute_path))
        pid = _link_program([cs])
        return ShaderProgram(program=int(pid))

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