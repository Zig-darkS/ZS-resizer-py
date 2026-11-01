"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, ffmpeg
from .errors import FFmpegError, SizingError
from .pipeline import Job, run_batch
from .sizing import Fit

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif",
    ".tif", ".tiff", ".bmp",
}


def _collect(sources: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for p in sources:
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files.extend(f for f in it if f.is_file() and f.suffix.lower() in IMAGE_EXTS)
        elif p.is_file():
            files.append(p)
        else:
            raise SystemExit(f"no such file or directory: {p}")
    return sorted(set(files))


def _output_path(src: Path, args: argparse.Namespace, single: bool) -> Path:
    if args.output:
        if not single:
            raise SystemExit("--output requires exactly one source file")
        return Path(args.output)

    base = Path(args.output_dir) if args.output_dir else src.parent
    suffix = args.suffix
    # If user gave no location hint at all, default suffix to avoid clobbering source.
    if not suffix and not args.output_dir:
        suffix = "_resized"

    dst = base / (src.stem + suffix + src.suffix)
    if dst.resolve() == src.resolve():
        raise SystemExit(
            f"refusing to write output over source: {src}\n"
            f"hint: use --suffix, --output-dir, or -o"
        )
    return dst


def _cmd_doctor(args: argparse.Namespace) -> int:
    try:
        info = ffmpeg.probe(args.ffmpeg_path)
    except FFmpegError as e:
        print(f"FFmpeg: NOT AVAILABLE — {e}", file=sys.stderr)
        return 1
    print(f"FFmpeg: {info.version}")
    print(f"  path:   {info.path}")
    print(f"  zscale: {'yes' if info.has_zscale else 'no'}")
    for enc in ("mjpeg", "libwebp", "libaom-av1", "libsvtav1"):
        print(f"  encoder {enc:<12}: {'yes' if enc in info.encoders else 'no'}")
    return 0


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="zs-resizer",
        description="Fast Lanczos image resizer (FFmpeg).",
    )
    p.add_argument("--version", action="version", version=f"zs-resizer {__version__}")
    p.add_argument("--doctor", action="store_true", help="check FFmpeg capabilities and exit")
    p.add_argument("sources", nargs="*", type=Path, help="files or directories")

    p.add_argument("-w", "--width", type=int)
    p.add_argument("-H", "--height", type=int)
    p.add_argument("--fit", choices=["inside", "cover", "fill", "pad"], default="inside")
    p.add_argument("-q", "--quality", type=int, default=90, help="1..100, higher = better")
    p.add_argument("--engine", choices=["auto", "zscale", "swscale"], default="auto")
    p.add_argument("--strip-metadata", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("-o", "--output", help="exact output path (single source only)")
    p.add_argument("--output-dir", help="directory for outputs")
    p.add_argument("--suffix", default="", help="suffix added to output filename, e.g. _1920")
    p.add_argument("-j", "--jobs", type=int, default=None, help="parallel workers")
    p.add_argument("--ffmpeg-path")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)

    if args.doctor:
        return _cmd_doctor(args)

    if not args.sources:
        print("error: no input files. Try --doctor first.", file=sys.stderr)
        return 2
    if args.width is None and args.height is None:
        print("error: pass --width and/or --height", file=sys.stderr)
        return 2

    files = _collect(args.sources, args.recursive)
    if not files:
        print("error: no images matched", file=sys.stderr)
        return 2

    single = len(files) == 1
    jobs = [
        Job(
            src=src,
            dst=_output_path(src, args, single),
            width=args.width,
            height=args.height,
            fit=args.fit,
            quality=args.quality,
            engine=args.engine,
            strip_metadata=args.strip_metadata,
            overwrite=args.overwrite,
            ffmpeg_path=args.ffmpeg_path,
        )
        for src in files
    ]

    results = run_batch(jobs, workers=args.jobs)
    ok = sum(1 for r in results if r.ok)
    for r in results:
        if r.ok:
            print(f"ok   {r.src} -> {r.dst}")
        else:
            print(f"FAIL {r.src}: {r.error}", file=sys.stderr)
    print(f"\n{ok}/{len(results)} done")
    return 0 if ok == len(results) else 1
