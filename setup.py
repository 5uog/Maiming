# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: setup.py
from __future__ import annotations

from pathlib import Path
import sys
from setuptools import Extension, setup

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_CYTHON_BUILD_DIR = _ROOT / "build" / "cython"
_CYTHON_MODULES: tuple[str, ...] = ("ludoxel.core.geometry.intersection", "ludoxel.core.grid.voxel_dda", "ludoxel.core.math.view_angles")


def _wants_build_ext(argv: list[str]) -> bool:
    cmds = {str(a).strip().lower() for a in argv[1:]}
    return "build_ext" in cmds


def _module_source_path(module_name: str) -> str:
    rel = Path(*str(module_name).split(".")).with_suffix(".py")
    return str(_SRC / rel)


def _base_extensions() -> list[Extension]:
    return [Extension(name=str(mod), sources=[_module_source_path(str(mod))]) for mod in _CYTHON_MODULES]


def _cythonized_extensions() -> list[Extension]:
    try:
        from Cython.Build import cythonize
    except ModuleNotFoundError as exc:
        raise RuntimeError("Cython is required for the explicit local native-extension build path. Run `python -m pip install -e \".[dev]\" --no-build-isolation` first, then rerun `python .\\setup.py build_ext --inplace`.") from exc
    return cythonize(_base_extensions(), build_dir=str(_CYTHON_BUILD_DIR), compiler_directives={"language_level": 3, "boundscheck": False, "wraparound": False, "initializedcheck": False}, annotate=False, nthreads=0)


def main() -> None:
    ext_modules = _cythonized_extensions() if _wants_build_ext(sys.argv) else []
    setup(ext_modules=ext_modules)


if __name__ == "__main__":
    main()
