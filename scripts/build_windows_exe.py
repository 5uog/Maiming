# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import argparse
import os
import shutil
import subprocess
import sys
import time

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Windows onefile executable with bundled PyInstaller data for the repository src/ tree, assets/, and the compiled native hot-path extensions.")
    parser.add_argument("--skip-native-build", action="store_true", help="Skip the in-place native-extension build step before packaging.")
    parser.add_argument("--keep-build-cache", action="store_true", help="Preserve the per-run PyInstaller work and spec directories instead of discarding them after packaging.")
    return parser.parse_args()

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _run(cmd: list[str], *, cwd: Path) -> None:
    print(subprocess.list2cmdline(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)

def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

def _remove_tree_best_effort(path: Path) -> None:
    try:
        _remove_tree(path)
    except Exception:
        pass

def _add_data_arg(source: Path, destination: str) -> str:
    return str(source.resolve()) + os.pathsep + str(destination)

def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyInstaller is required for the Windows executable build. Install the development dependencies with `python -m pip install -e \".[dev]\"` before rerunning this script.") from exc

def _windows_executable_icon_path(root: Path) -> Path | None:
    candidate = root / "assets" / "ui" / "app_icon.ico"
    if candidate.is_file():
        return candidate.resolve()
    return None

def _pyinstaller_session_token() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + f"-pid{int(os.getpid())}"

def _pyinstaller_session_paths(root: Path) -> tuple[str, Path, Path, Path]:
    token = _pyinstaller_session_token()
    work_path = root / "build" / "pyinstaller-runs" / token
    spec_path = root / "build" / "pyinstaller-spec-runs" / token
    stage_dist_path = root / "build" / "pyinstaller-dist-runs" / token
    work_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    stage_dist_path.parent.mkdir(parents=True, exist_ok=True)
    return (token, work_path, spec_path, stage_dist_path)

def _legacy_onedir_output_path(root: Path) -> Path:
    return root / "dist" / "windows" / "Ludoxel"

def _published_output_path(root: Path) -> Path:
    return root / "dist" / "windows" / "Ludoxel.exe"

def _publish_legal_materials(root: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for name in ("LICENSE", "NOTICE"):
        source = root / name
        if source.is_file():
            shutil.copy2(str(source), str(destination_dir / name))

    licenses_source = root / "licenses"
    if licenses_source.is_dir():
        licenses_destination = destination_dir / "licenses"
        if licenses_destination.exists():
            shutil.rmtree(licenses_destination)
        shutil.copytree(str(licenses_source), str(licenses_destination))

def _publish_staged_executable(staged_executable_path: Path, *, published_executable_path: Path) -> tuple[Path, bool]:
    published_executable_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(str(staged_executable_path), str(published_executable_path))
    except PermissionError:
        return (staged_executable_path, False)
    return (published_executable_path, True)

def build_native_extensions(root: Path) -> None:
    _run([sys.executable, str(root / "scripts" / "build_native_extensions.py")], cwd=root)

def build_windows_bundle(root: Path, *, keep_build_cache: bool) -> tuple[Path, bool]:
    published_executable_path = _published_output_path(root)
    _token, work_path, spec_path, stage_dist_path = _pyinstaller_session_paths(root)
    executable_icon_path = _windows_executable_icon_path(root)
    legacy_onedir_output_path = _legacy_onedir_output_path(root)

    _remove_tree_best_effort(legacy_onedir_output_path)
    _remove_tree_best_effort(stage_dist_path)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "Ludoxel",
        "--distpath",
        str(stage_dist_path),
        "--workpath",
        str(work_path),
        "--specpath",
        str(spec_path),
        "--paths",
        str(root / "src"),
        "--collect-data",
        "ludoxel",
        "--collect-submodules",
        "ludoxel",
        "--add-data",
        _add_data_arg(root / "assets", "assets"),
        "--add-data",
        _add_data_arg(root / "src", "src"),
    ]
    if executable_icon_path is not None:
        cmd.extend(["--icon", str(executable_icon_path)])
    cmd.append(str(root / "src" / "ludoxel" / "__main__.py"))
    stage_executable_path = stage_dist_path / "Ludoxel.exe"
    try:
        _run(cmd, cwd=root)
    finally:
        if not bool(keep_build_cache):
            _remove_tree_best_effort(work_path)
            _remove_tree_best_effort(spec_path)
    _remove_tree_best_effort(legacy_onedir_output_path)
    if not stage_executable_path.is_file():
        raise RuntimeError(f"The PyInstaller staging executable was not produced at {stage_executable_path}.")
    _publish_legal_materials(root, stage_dist_path)
    output_path, published = _publish_staged_executable(stage_executable_path, published_executable_path=published_executable_path)
    if bool(published):
        _publish_legal_materials(root, published_executable_path.parent)
    if bool(published) and not bool(keep_build_cache):
        _remove_tree_best_effort(stage_dist_path)
    return (output_path, bool(published))

def main() -> int:
    if not sys.platform.startswith("win"):
        raise RuntimeError("This packaging script targets Windows onefile executable bundles and must be run on Windows.")

    args = parse_args()
    root = project_root()
    _ensure_pyinstaller()
    if not bool(args.skip_native_build):
        build_native_extensions(root)
    output_path, published = build_windows_bundle(root, keep_build_cache=bool(args.keep_build_cache))
    if bool(published):
        print(f"published executable: {output_path}")
        print(f"entry point: {output_path}")
    else:
        print(f"staged executable: {output_path}")
        print(f"publish target remained locked: {_published_output_path(root)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
