# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/api/run.py
from __future__ import annotations

from pathlib import Path


def _search_start(start: Path) -> Path:
    p = Path(start).resolve()
    return p.parent if p.is_file() else p


def _is_project_root(path: Path) -> bool:
    p = Path(path)
    if (p / "pyproject.toml").exists():
        return True
    return (p / "assets").exists() and (p / "src").exists()


def _find_project_root(start: Path) -> Path:
    p = _search_start(start)

    for _ in range(16):
        if _is_project_root(p):
            return p
        if p.parent == p:
            break
        p = p.parent

    return _search_start(start)


def run_app() -> None:
    from ..presentation.windows.main_window import run_app as _run

    project_root = _find_project_root(Path(__file__))
    _run(project_root=project_root)
