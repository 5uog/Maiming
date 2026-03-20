# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

def _start_directory(path: Path) -> Path:
    resolved = Path(path).resolve()
    return resolved.parent if resolved.is_file() else resolved

def _is_project_root(path: Path) -> bool:
    root = Path(path).resolve()
    if (root / "pyproject.toml").is_file():
        return True
    return (root / "assets").is_dir() and (root / "src").is_dir()

def _search_project_root(start: Path) -> Path | None:
    cursor = _start_directory(start)

    while True:
        if _is_project_root(cursor):
            return cursor

        parent = cursor.parent
        if parent == cursor:
            return None
        cursor = parent

def _find_project_root(start: Path) -> Path:
    module_root = _search_project_root(start)
    if module_root is not None:
        return module_root

    working_root = _search_project_root(Path.cwd())
    if working_root is not None:
        return working_root

    return _start_directory(start)

def run_app() -> None:
    from ...shared.presentation.qt.windows.main_window import run_app as _run

    project_root = _find_project_root(Path(__file__))
    _run(project_root=project_root)