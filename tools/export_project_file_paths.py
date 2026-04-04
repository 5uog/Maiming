#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_EXCLUDE_PARTS: tuple[str, ...] = ("__pycache__", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "venv", "build", "dist")
DEFAULT_ROOT_FILES: tuple[str, ...] = ("MANIFEST.in", "pyproject.toml", "README.md", "NOTICE")

def _project_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent

def _split_csv(raw: str) -> tuple[str, ...]:
    items = [piece.strip() for piece in raw.split(",") if piece.strip()]
    return tuple(dict.fromkeys(items))

def _is_excluded(path: Path, src_root: Path, exclude_parts: tuple[str, ...]) -> bool:
    try:
        rel_parts = path.relative_to(src_root).parts
    except ValueError:
        rel_parts = path.parts
    excluded = set(exclude_parts)
    return any(part in excluded for part in rel_parts)

def _iter_src_files(src_root: Path, exclude_parts: tuple[str, ...]) -> Iterable[Path]:
    files: list[Path] = []
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        if _is_excluded(path, src_root, exclude_parts):
            continue
        files.append(path)
    files.sort(key=lambda p: p.relative_to(src_root).as_posix())
    return files

def _iter_root_files(project_root: Path, root_files: tuple[str, ...]) -> Iterable[Path]:
    files: list[Path] = []
    for raw in root_files:
        candidate = (project_root / raw).resolve()
        try:
            candidate.relative_to(project_root.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            files.append(candidate)
    files.sort(key=lambda p: p.relative_to(project_root).as_posix())
    return files

def _collect_target_files(project_root: Path, src_root: Path, exclude_parts: tuple[str, ...], root_files: tuple[str, ...]) -> list[Path]:
    if not src_root.is_dir():
        raise FileNotFoundError(f"src directory not found: {src_root}")

    files: list[Path] = []
    files.extend(_iter_src_files(src_root, exclude_parts))
    files.extend(_iter_root_files(project_root, root_files))
    files.sort(key=lambda p: p.relative_to(project_root).as_posix())
    return files

def build_dump(project_root: Path, src_root: Path, exclude_parts: tuple[str, ...], root_files: tuple[str, ...]) -> tuple[str, int]:
    files = _collect_target_files(project_root=project_root, src_root=src_root, exclude_parts=exclude_parts, root_files=root_files)
    lines = [f"PROJECT_ROOT: {project_root.resolve().as_posix()}", f"SOURCE_ROOT: {src_root.resolve().as_posix()}", f"FILE_COUNT: {len(files)}", ""]
    lines.extend(path.relative_to(project_root).as_posix() for path in files)
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text = f"{text}\n"
    return text, len(files)

def parse_args() -> argparse.Namespace:
    project_root = _project_root_from_script()
    default_src = project_root / "src"
    default_output = project_root / ".artifacts" / "file_paths" / "project_file_paths.txt"

    parser = argparse.ArgumentParser(description="Export relative file paths for all files under src/ plus selected root files into a single txt file.")
    parser.add_argument("--root", type=Path, default=project_root, help=f"project root directory (default: {project_root})")
    parser.add_argument("--src", type=Path, default=default_src, help=f"source root to scan recursively (default: {default_src})")
    parser.add_argument("--output", type=Path, default=default_output, help=f"output txt file path (default: {default_output})")
    parser.add_argument("--exclude-parts", type=_split_csv, default=DEFAULT_EXCLUDE_PARTS, help=("comma-separated directory names to skip if they appear anywhere under src " f"(default: {','.join(DEFAULT_EXCLUDE_PARTS)})"))
    parser.add_argument("--root-files", type=_split_csv, default=DEFAULT_ROOT_FILES, help=("comma-separated project-root relative file paths to include outside src " f"(default: {','.join(DEFAULT_ROOT_FILES)})"))
    parser.add_argument("--stdout", action="store_true", help="write the result to stdout instead of a file")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    project_root = args.root.resolve()
    src_root = args.src.resolve()
    output_path = args.output.resolve()

    try:
        text, count = build_dump(project_root=project_root, src_root=src_root, exclude_parts=args.exclude_parts, root_files=args.root_files)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.write(text)
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {count} file(s) to {output_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
