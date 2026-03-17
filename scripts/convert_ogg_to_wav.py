# FILE: scripts/convert_ogg_to_wav.py
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = PROJECT_ROOT / "assets"

_EXCLUDED_RELATIVE_PREFIXES: tuple[Path, ...] = (
    Path("ambient/my_world"),
    Path("audio/ambient/my_world"),
)


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg was not found on PATH", file=sys.stderr)
        raise SystemExit(1)


def require_assets_root() -> None:
    if not ASSETS_ROOT.exists():
        print(f"error: assets directory does not exist: {ASSETS_ROOT}", file=sys.stderr)
        raise SystemExit(1)
    if not ASSETS_ROOT.is_dir():
        print(f"error: assets path is not a directory: {ASSETS_ROOT}", file=sys.stderr)
        raise SystemExit(1)


def is_excluded(src: Path) -> bool:
    try:
        relative = src.resolve().relative_to(ASSETS_ROOT.resolve())
    except Exception:
        return False

    for prefix in _EXCLUDED_RELATIVE_PREFIXES:
        parts = prefix.parts
        if relative.parts[: len(parts)] == parts:
            return True
    return False


def collect_ogg_files() -> list[Path]:
    files = [
        path
        for path in ASSETS_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".ogg"
        and not is_excluded(path)
    ]
    files.sort()
    return files


def destination_for(src: Path) -> Path:
    return src.with_suffix(".wav")


def convert_one(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(src),
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"failed: {src}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        return False

    if not dst.is_file():
        print(f"failed: output was not created: {dst}", file=sys.stderr)
        return False

    try:
        src.unlink()
    except Exception as exc:
        print(f"failed: converted but could not delete source: {src}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return False

    print(f"ok: {src} -> {dst} (source deleted)")
    return True


def main() -> int:
    require_ffmpeg()
    require_assets_root()

    ogg_files = collect_ogg_files()
    if not ogg_files:
        print("done: no eligible .ogg files were found")
        return 0

    success_count = 0
    failure_count = 0

    for src in ogg_files:
        dst = destination_for(src)
        ok = convert_one(src, dst)
        if ok:
            success_count += 1
        else:
            failure_count += 1

    print(f"done: success={success_count} failed={failure_count}")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
