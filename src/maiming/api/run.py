# FILE: src/maiming/api/run.py
from __future__ import annotations

from pathlib import Path

def _find_project_root(start: Path) -> Path:
    """
    This resolver walks upward from a known module location and selects the first directory
    that plausibly represents the repository root. The heuristic prefers a pyproject.toml
    anchor and preserves existing runtime expectations such as a top-level assets directory.
    """
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent

    for _ in range(16):
        if (p / "pyproject.toml").exists():
            if (p / "assets").exists():
                return p
            return p
        if (p / "assets").exists() and (p / "src").exists():
            return p
        if p.parent == p:
            break
        p = p.parent

    return Path(start).resolve().parent

def run_app() -> None:
    from maiming.presentation.windows.main_window import run_app as _run
    project_root = _find_project_root(Path(__file__))
    _run(project_root=project_root)