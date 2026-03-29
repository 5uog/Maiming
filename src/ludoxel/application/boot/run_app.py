# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from pathlib import Path
import sys

from ...shared.project_paths import default_project_root, default_resource_root, is_frozen_application


def _preferred_python_314(project_root: Path) -> Path | None:
    local_app_data = os.environ.get("LocalAppData", "").strip()
    candidates: list[Path] = []
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Python" / "Python314" / "python.exe")

    current_exe = Path(sys.executable).resolve()
    current_parent = current_exe.parent
    if str(current_parent.name).startswith("Python31"):
        candidates.append(current_parent.parent / "Python314" / "python.exe")

    for candidate in candidates:
        resolved = Path(candidate).resolve()
        if not resolved.is_file():
            continue
        if resolved == current_exe:
            continue
        return resolved
    return None


def _ensure_python_314(project_root: Path) -> None:
    if is_frozen_application():
        return
    if sys.version_info[:2] == (3, 14):
        return

    candidate = _preferred_python_314(project_root)
    if candidate is None:
        return

    main_py = project_root / "main.py"
    if not main_py.is_file():
        return

    os.execv(str(candidate),[str(candidate), str(main_py), *sys.argv[1:]])


def run_app() -> None:
    project_root = default_project_root(Path(__file__))
    resource_root = default_resource_root(Path(__file__))
    _ensure_python_314(project_root)

    from ludoxel.shared.ui.main_window import run_app as _run

    _run(project_root=project_root, resource_root=resource_root)
