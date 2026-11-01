"""FFmpeg discovery, capability probing, command construction."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .errors import FFmpegError
from .sizing import ResizePlan


@dataclass(frozen=True)
class FFmpegInfo:
    path: str
    version: str
    has_zscale: bool
    encoders: frozenset[str]


def _resolve(explicit: str | None) -> str:
    for candidate in (explicit, os.environ.get("FFMPEG_PATH")):
        if candidate:
            p = Path(candidate)
            if p.is_file():
                return str(p)
            raise FFmpegError(f"ffmpeg not found at {candidate}")
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FFmpegError(
        "ffmpeg binary not found. Install ffmpeg or set FFMPEG_PATH / --ffmpeg-path."
    )


def _run(path: str, *args: str) -> str:
    try:
        return subprocess.run(
            [path, "-hide_banner", *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise FFmpegError(f"failed to run {path} {' '.join(args)}: {e}") from e


@lru_cache(maxsize=None)
def probe(explicit_path: str | None = None) -> FFmpegInfo:
    path = _resolve(explicit_path)
    version_out = _run(path, "-version")
    version = version_out.splitlines()[0].split(" Copyright")[0].strip()

    filters = _run(path, "-filters")
    has_zscale = bool(re.search(r"\bzscale\b", filters))

    enc_out = _run(path, "-encoders")
    encoders = frozenset(
        line.split()[1]
        for line in enc_out.splitlines()
        if line.startswith(" V") and len(line.split()) >= 2
    )
    return FFmpegInfo(path=path, version=version, has_zscale=has_zscale, encoders=encoders)


def _ffprobe_for(ffmpeg_path: str) -> str:
    p = Path(ffmpeg_path)
    name = "ffprobe.exe" if p.suffix.lower() == ".exe" else "ffprobe"
    beside = p.with_name(name)
    if beside.is_file():
        return str(beside)
    found = shutil.which("ffprobe")
    if found:
        return found
    raise FFmpegError("ffprobe not found; install alongside ffmpeg or add to PATH")


def probe_size(path: Path, ffmpeg_path: str | None = None) -> tuple[int, int]:
    ffprobe = _ffprobe_for(probe(ffmpeg_path).path)
    out = _run(
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(path),
    ).strip()
    try:
        w, h = out.split(",")[:2]
        return int(w), int(h)
    except ValueError as e:
        raise FFmpegError(f"could not read dimensions of {path}: {out!r}") from e


def quality_args(fmt: str, quality: int) -> list[str]:
    """Map 1..100 (higher = better) onto encoder-specific knobs."""
    q = max(1, min(100, quality))
    if fmt in ("jpg", "jpeg"):
        qv = round(31 - (q - 1) * (31 - 2) / 99)
        return ["-q:v", str(qv)]
    if fmt == "webp":
        return ["-quality", str(q)]
    if fmt == "avif":
        crf = round(63 - (q - 1) * (63 - 10) / 99)
        return ["-crf", str(crf)]
    if fmt == "png":
        return ["-compression_level", "9"]
    return []


def build_command(
    *,
    src: Path,
    dst: Path,
    plan: ResizePlan,
    quality: int = 90,
    engine: str = "auto",
    strip_metadata: bool = False,
    overwrite: bool = False,
    ffmpeg_path: str | None = None,
) -> list[str]:
    info = probe(ffmpeg_path)
    fmt = dst.suffix.lower().lstrip(".")
    if not fmt:
        raise FFmpegError(f"output path has no extension: {dst}")

    use_zscale = engine == "zscale" or (engine == "auto" and info.has_zscale)
    if use_zscale:
        filters = [
            f"zscale=w={plan.scale_width}:h={plan.scale_height}:filter=lanczos"
        ]
    else:
        filters = [
            f"scale={plan.scale_width}:{plan.scale_height}:flags=lanczos"
        ]

    if plan.crop:
        cx = (plan.scale_width - plan.out_width) // 2
        cy = (plan.scale_height - plan.out_height) // 2
        filters.append(f"crop={plan.out_width}:{plan.out_height}:{cx}:{cy}")

    if plan.pad:
        px = (plan.out_width - plan.scale_width) // 2
        py = (plan.out_height - plan.scale_height) // 2
        filters.append(
            f"pad={plan.out_width}:{plan.out_height}:{px}:{py}:color=black"
        )

    if fmt == "avif":
        cmd_extra = []
        for enc in ("libsvtav1", "libaom-av1"):
            if enc in info.encoders:
                cmd_extra = ["-c:v", enc]
                break
        else:
            raise FFmpegError(
                "no AV1 encoder available (need libsvtav1 or libaom-av1); "
                "rebuild FFmpeg or pick a different output format"
            )
    else:
        cmd_extra = []

    cmd = [
        info.path,
        "-y" if overwrite else "-n",
        "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vf", ",".join(filters),
        "-frames:v", "1",
        "-update", "1",
    ]
    cmd += quality_args(fmt, quality)
    if strip_metadata:
        cmd += ["-map_metadata", "-1"]
    cmd += cmd_extra
    cmd.append(str(dst))
    return cmd
