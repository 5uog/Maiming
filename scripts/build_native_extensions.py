# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from importlib.util import find_spec
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path

import argparse
import os
import subprocess
import sys

from setuptools import Distribution, Extension
from setuptools.command.build_ext import build_ext

_HOT_PATH_MODULES: tuple[str, ...] = (
    "ludoxel.shared.math.geometry.ray_aabb",
    "ludoxel.shared.math.voxel.voxel_dda",
    "ludoxel.shared.math.view_angles",
)
_CYTHON_BUILD_DIR_NAME = "cython"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the native hot-path extensions in place and verify that imports resolve to compiled extension modules.")
    parser.add_argument("--skip-verify", action="store_true", help="Skip the post-build import verification step.")
    return parser.parse_args()

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _module_source_path(root: Path, module_name: str) -> str:
    return str(root / "src" / Path(*str(module_name).split(".")).with_suffix(".py"))

def _base_extensions(root: Path) -> list[Extension]:
    return [Extension(name=str(module_name), sources=[_module_source_path(root, str(module_name))]) for module_name in _HOT_PATH_MODULES]

def _cythonized_extensions(root: Path) -> list[Extension]:
    from Cython.Build import cythonize

    return cythonize(_base_extensions(root), build_dir=str(root / "build" / str(_CYTHON_BUILD_DIR_NAME)), compiler_directives={"language_level": 3, "boundscheck": False, "wraparound": False, "initializedcheck": False}, annotate=False, nthreads=0)

def _ensure_build_requirements() -> None:
    missing: list[str] = []
    if find_spec("setuptools") is None:
        missing.append("setuptools")
    if find_spec("Cython") is None:
        missing.append("Cython")
    if missing:
        raise RuntimeError("The in-place native build requires the development dependencies. Install them with `python -m pip install -e \".[dev]\"` before rerunning this script. Missing modules: " + ", ".join(missing))

def _env_with_src(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    src = str(root / "src")
    existing = str(env.get("PYTHONPATH", "")).strip()
    env["PYTHONPATH"] = src if not existing else src + os.pathsep + existing
    return env

def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(subprocess.list2cmdline(cmd))
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)

def _imported_module_path(*, root: Path, module_name: str) -> Path:
    env = _env_with_src(root)
    probe = "import importlib; module = importlib.import_module(%r); print(module.__file__)" % str(module_name)
    completed = subprocess.run([sys.executable, "-c", probe], cwd=str(root), env=env, check=True, capture_output=True, text=True)
    return Path(str(completed.stdout).strip())

def _is_extension_module_path(path: Path) -> bool:
    normalized = str(path).lower()
    return any(normalized.endswith(str(suffix).lower()) for suffix in EXTENSION_SUFFIXES)

def verify_extensions(root: Path) -> None:
    failures: list[str] = []
    for module_name in _HOT_PATH_MODULES:
        module_path = _imported_module_path(root=root, module_name=str(module_name))
        print(f"{module_name} -> {module_path}")
        if not _is_extension_module_path(module_path):
            failures.append(f"{module_name} resolved to {module_path}")
    if failures:
        raise RuntimeError("The native build completed, but one or more hot-path modules still resolved to Python sources:\n" + "\n".join(failures))

def build_extensions(root: Path) -> None:
    distribution = Distribution({"package_dir": {"": "src"}, "ext_modules": _cythonized_extensions(root)})
    command = build_ext(distribution)
    command.initialize_options()
    command.inplace = True
    command.build_temp = str(root / "build" / "temp")
    command.build_lib = str(root / "src")
    command.ensure_finalized()
    command.run()

def main() -> int:
    args = parse_args()
    root = project_root()
    _ensure_build_requirements()
    build_extensions(root)
    if not bool(args.skip_verify):
        verify_extensions(root)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
