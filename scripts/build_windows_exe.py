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

"""
I use this command-line module to construct the supported Windows executable distribution of Ludoxel by composing an optional narrow native-extension rebuild with a PyInstaller onefile packaging transform over the repository root.

Let root denote the repository root. Let N(root) be the optional native rebuild executed through `scripts/build_native_extensions.py`, and let P(root) be the PyInstaller image transform defined by the command family

    python -m PyInstaller --onefile --windowed --name Ludoxel ...

with analysis path rooted at `src/` and with explicit data transport for the repository-level `assets/` tree and the repository-level `src/` tree. I define the operational map

    B(root; native, cache) = P(root), if native = False
    B(root; native, cache) = P(root) o N(root), if native = True

where `cache` determines whether the uniquely allocated per-run PyInstaller work and spec directories are retained after packaging or are discarded on a best-effort basis once packaging has completed.

The generated bundle is intentionally single-file based at the user-visible shell boundary. If E is the emitted executable path and I(E) is the PyInstaller bundle-data root that is exposed at runtime through `sys._MEIPASS`, then I require

    E = root / dist / windows / Ludoxel.exe
    I(E) contains assets/
    I(E) contains src/

at bundle creation time. Under this contract, runtime initialization is not permitted to synthesize repository-level resource trees such as `assets/` or `src/` beside the executable on first launch. The only mutable repository-level subtree that the running application is intended to create beside the executable during ordinary operation is `configs/`. The embedded PyInstaller bootloader still materializes its internal extraction image in the runtime temporary directory represented by `sys._MEIPASS`, because that extraction step is a property of PyInstaller onefile execution rather than an application-level deployment tree emitted beside the executable.

I optionally admit a Windows executable icon resource at

    root / assets / ui / app_icon.ico

and, when that file exists, I extend the PyInstaller transform with `--icon` so that the emitted `Ludoxel.exe` carries the intended shell icon resource instead of the default PyInstaller mark.

The packaging precondition is the presence of the PyInstaller module in the active interpreter. Formally, if

    import_spec(PyInstaller) = None

then the packaging operator is undefined and I reject execution immediately.

I use the following invocation forms.

    python scripts/build_windows_exe.py
    python scripts/build_windows_exe.py --skip-native-build
    python scripts/build_windows_exe.py --keep-build-cache
    python scripts/build_windows_exe.py --skip-native-build --keep-build-cache

The default state executes the narrow native rebuild first and then emits the onefile Windows executable. The `--skip-native-build` state suppresses that preliminary rebuild and therefore admits a pure-Python executable image if the compiled hot-path kernels are absent. The `--keep-build-cache` state preserves the per-run PyInstaller work and spec directories for iterative packaging work. I allocate those intermediate directories under run-specific session roots so that a locked cache from a previous build cannot block the next packaging attempt merely because an older PyInstaller child process or file handle still exists. I also route the raw PyInstaller executable into a run-specific staging directory under `build/` before publishing it to `dist/windows/Ludoxel.exe`. Therefore, if the published executable is locked by a running process, the build itself remains valid and I preserve the staged executable instead of failing during the final publish step. I return process status 0 exactly when the platform guard, dependency guard, optional native build, and PyInstaller packaging transform all complete without failure. I therefore use this module as the canonical deterministic Windows distribution builder for Ludoxel.
"""


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
