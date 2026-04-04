# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import argparse
import shutil
import sys

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Remove repository-local __pycache__ directories, the top-level build directory, and generated .pyd files under src/ludoxel/shared/math."))
    parser.add_argument("--dry-run", action="store_true", help="Print deletion targets without removing them.")
    parser.add_argument("--include-venv-caches", action="store_true", help="Also remove __pycache__ directories inside common virtual-environment directories.")
    return parser.parse_args()

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def should_skip_path(path: Path, include_venv_caches: bool) -> bool:
    parts = set(path.parts)

    if ".git" in parts:
        return True

    if include_venv_caches:
        return False

    return any(name in parts for name in (".venv", "venv", "env"))

def collect_pycache_dirs(root: Path, include_venv_caches: bool) -> list[Path]:
    matches: list[Path] = []
    for path in root.rglob("__pycache__"):
        if not path.is_dir():
            continue
        if should_skip_path(path, include_venv_caches):
            continue
        matches.append(path)

    matches.sort()
    return matches

def collect_pyd_files(root: Path) -> list[Path]:
    math_root = root / "src" / "ludoxel" / "shared" / "math"
    if not math_root.is_dir():
        return []

    matches = [path for path in math_root.rglob("*.pyd") if path.is_file()]
    matches.sort()
    return matches

def remove_directory(path: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"would remove directory: {path}")
        return True

    try:
        shutil.rmtree(path)
        print(f"removed directory: {path}")
        return True
    except FileNotFoundError:
        print(f"missing directory: {path}")
        return True
    except Exception as exc:
        print(f"failed to remove directory: {path}: {exc}", file=sys.stderr)
        return False

def remove_file(path: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"would remove file: {path}")
        return True

    try:
        path.unlink()
        print(f"removed file: {path}")
        return True
    except FileNotFoundError:
        print(f"missing file: {path}")
        return True
    except Exception as exc:
        print(f"failed to remove file: {path}: {exc}", file=sys.stderr)
        return False

def main() -> int:
    args = parse_args()
    root = project_root()

    pycache_dirs = collect_pycache_dirs(root=root, include_venv_caches=args.include_venv_caches)
    build_dir = root / "build"
    pyd_files = collect_pyd_files(root)

    failure_count = 0

    for path in pycache_dirs:
        if not remove_directory(path, dry_run=args.dry_run):
            failure_count += 1

    if build_dir.exists():
        if not remove_directory(build_dir, dry_run=args.dry_run):
            failure_count += 1
    else:
        print(f"missing directory: {build_dir}")

    for path in pyd_files:
        if not remove_file(path, dry_run=args.dry_run):
            failure_count += 1

    print(f"pycache_dirs: {len(pycache_dirs)} " f"pyd_files: {len(pyd_files)} " f"failures: {failure_count}")
    if int(len(pyd_files)) > 0:
        if bool(args.dry_run):
            print("dry-run note: removing the generated hot-path extension modules would return the renderer to the pure-Python math kernels until scripts/build_native_extensions.py is rerun.")
        else:
            print("note: the generated hot-path extension modules were removed. Performance-sensitive runs should rebuild them with scripts/build_native_extensions.py before launching Ludoxel again.")
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
