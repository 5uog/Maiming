#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_EXTENSIONS: tuple[str, ...] = (".py", ".glsl", ".vert", ".frag", ".geom", ".comp", ".tesc", ".tese", ".qss")
LANGUAGE_BY_SUFFIX: dict[str, str] = {".py": "py", ".glsl": "glsl", ".vert": "glsl", ".frag": "glsl", ".geom": "glsl", ".comp": "glsl", ".tesc": "glsl", ".tese": "glsl", ".qss": "qss"}
DEFAULT_EXCLUDE_PARTS: tuple[str, ...] = ("__pycache__", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "venv", "build", "dist")

def _project_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent

def _parse_extensions(raw: str) -> tuple[str, ...]:
    items: list[str] = []
    for piece in raw.split(","):
        item = piece.strip()
        if not item:
            continue
        if not item.startswith("."):
            item = f".{item}"
        items.append(item.lower())
    if not items:
        raise argparse.ArgumentTypeError("extensions must not be empty")
    return tuple(dict.fromkeys(items))

def _split_csv(raw: str) -> tuple[str, ...]:
    items = [piece.strip() for piece in raw.split(",") if piece.strip()]
    return tuple(dict.fromkeys(items))

def _language_for(path: Path) -> str:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "text")

def _max_backtick_run(text: str) -> int:
    best = 0
    current = 0
    for ch in text:
        if ch == "`":
            current += 1
            if current > best:
                best = current
        else:
            current = 0
    return best

def _fence_for(text: str) -> str:
    return "`" * max(3, _max_backtick_run(text) + 1)

def _is_excluded(path: Path, src_root: Path, exclude_parts: tuple[str, ...]) -> bool:
    try:
        rel_parts = path.relative_to(src_root).parts
    except ValueError:
        rel_parts = path.parts
    excluded = set(exclude_parts)
    return any(part in excluded for part in rel_parts)

def _iter_target_files(src_root: Path, extensions: tuple[str, ...], exclude_parts: tuple[str, ...]) -> Iterable[Path]:
    allowed = {ext.lower() for ext in extensions}
    files: list[Path] = []
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        if _is_excluded(path, src_root, exclude_parts):
            continue
        if path.suffix.lower() not in allowed:
            continue
        files.append(path)
    files.sort(key=lambda p: p.relative_to(src_root).as_posix())
    return files

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"UTF-8 decode failed: {path}") from exc

def _render_entry(path: Path, src_root: Path) -> str:
    rel = path.relative_to(src_root).as_posix()
    content = _read_text(path).replace("\r\n", "\n").replace("\r", "\n")
    fence = _fence_for(content)
    lang = _language_for(path)
    body = content if content.endswith("\n") else f"{content}\n"
    return (f"FILE: {rel}\n" f"{fence}{lang}\n" f"{body}" f"{fence}\n")

def build_dump(src_root: Path, extensions: tuple[str, ...], exclude_parts: tuple[str, ...]) -> tuple[str, int]:
    if not src_root.is_dir():
        raise FileNotFoundError(f"src directory not found: {src_root}")

    files = list(_iter_target_files(src_root, extensions, exclude_parts))
    lines = [f"SOURCE_ROOT: {src_root.resolve().as_posix()}", f"FILE_COUNT: {len(files)}", ""]
    chunks = ["\n".join(lines)]
    for index, path in enumerate(files):
        if index:
            chunks.append("\n")
        chunks.append(_render_entry(path, src_root))
    return "".join(chunks), len(files)

def parse_args() -> argparse.Namespace:
    project_root = _project_root_from_script()
    default_src = project_root / "src"
    default_output = project_root / ".artifacts" / "code_dump" / "src_code_blocks.txt"

    parser = argparse.ArgumentParser(description=("Collect code files under src/ and export them into a single txt file, wrapping each file in fenced code blocks."))
    parser.add_argument("--src", type=Path, default=default_src, help=f"source root to scan (default: {default_src})")
    parser.add_argument("--output", type=Path, default=default_output, help=f"output txt file path (default: {default_output})")
    parser.add_argument("--extensions", type=_parse_extensions, default=DEFAULT_EXTENSIONS, help=("comma-separated file extensions to include " f"(default: {','.join(DEFAULT_EXTENSIONS)})"))
    parser.add_argument("--exclude-parts", type=_split_csv, default=DEFAULT_EXCLUDE_PARTS, help=("comma-separated directory names to skip if they appear anywhere under src " f"(default: {','.join(DEFAULT_EXCLUDE_PARTS)})"))
    parser.add_argument("--stdout", action="store_true", help="write the result to stdout instead of a file")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    src_root = args.src.resolve()
    output_path = args.output.resolve()

    try:
        text, count = build_dump(src_root=src_root, extensions=args.extensions, exclude_parts=args.exclude_parts)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {count} file(s) to {output_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
