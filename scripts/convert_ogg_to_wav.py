# FILE: scripts/convert_ogg_to_wav.py
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert OGG audio files to PCM WAV files through ffmpeg.")
    parser.add_argument("input", type=Path, help="Input .ogg file or directory.")
    parser.add_argument("-o", "--output", type=Path, default=None, help=("Output .wav file or output directory. If omitted, I place each .wav next to its source."))
    parser.add_argument("--sample-rate", type=int, default=44100, help="Output sample rate in Hz.")
    parser.add_argument("--channels", type=int, default=2, help="Output channel count.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    return parser.parse_args()


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg was not found on PATH", file=sys.stderr)
        sys.exit(1)


def collect_ogg_files(input_path: Path) -> list[Path]:
    if not input_path.exists():
        print(f"error: input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.is_file():
        if input_path.suffix.lower() != ".ogg":
            print(f"error: input file is not an .ogg file: {input_path}", file=sys.stderr)
            sys.exit(1)
        return [input_path]

    files = [path for path in input_path.rglob("*") if path.is_file() and path.suffix.lower() == ".ogg"]
    files.sort()
    return files


def resolve_output_path(src: Path, input_root: Path, output_arg: Path | None, input_is_file: bool) -> Path:
    if output_arg is None:
        return src.with_suffix(".wav")

    if input_is_file:
        if output_arg.suffix.lower() == ".wav":
            return output_arg
        return output_arg / f"{src.stem}.wav"

    relative = src.relative_to(input_root).with_suffix(".wav")
    return output_arg / relative


def convert_one(src: Path, dst: Path, sample_rate: int, channels: int, overwrite: bool) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() and not overwrite:
        print(f"skip: {dst}")
        return True

    command = ["ffmpeg", "-y" if overwrite else "-n", "-v", "error", "-i", str(src), "-ar", str(sample_rate), "-ac", str(channels), "-c:a", "pcm_s16le", str(dst)]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)

    if result.returncode != 0:
        print(f"failed: {src}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        return False

    print(f"ok: {src} -> {dst}")
    return True


def main() -> int:
    args = parse_args()
    require_ffmpeg()

    input_path = args.input.resolve()
    input_is_file = input_path.is_file()
    input_root = input_path.parent if input_is_file else input_path

    ogg_files = collect_ogg_files(input_path)
    if not ogg_files:
        print("error: no .ogg files were found", file=sys.stderr)
        return 1

    success_count = 0
    failure_count = 0

    for src in ogg_files:
        dst = resolve_output_path(src=src, input_root=input_root, output_arg=args.output.resolve() if args.output is not None else None, input_is_file=input_is_file)
        ok = convert_one(src=src, dst=dst, sample_rate=args.sample_rate, channels=args.channels, overwrite=args.overwrite)
        if ok:
            success_count += 1
        else:
            failure_count += 1

    print(f"done: success={success_count} failed={failure_count}")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
