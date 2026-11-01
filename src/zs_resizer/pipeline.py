"""Batch orchestration over many files."""

from __future__ import annotations

import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import ffmpeg, sizing
from .errors import FFmpegError, SizingError


@dataclass(frozen=True)
class Job:
    src: Path
    dst: Path
    width: int | None
    height: int | None
    fit: str = "inside"
    quality: int = 90
    engine: str = "auto"
    strip_metadata: bool = False
    overwrite: bool = False
    ffmpeg_path: str | None = None


@dataclass(frozen=True)
class Result:
    src: Path
    dst: Path | None
    ok: bool
    error: str | None = None


def run_job(job: Job) -> Result:
    try:
        if job.src.resolve() == job.dst.resolve():
            return Result(
                job.src, None,
                ok=False,
                error="source and destination are the same file",
            )

        if job.dst.exists() and not job.overwrite:
            return Result(
                job.src, job.dst,
                ok=False,
                error="output exists (use --overwrite)",
            )

        src_w, src_h = ffmpeg.probe_size(job.src, job.ffmpeg_path)
        plan = sizing.compute_plan(src_w, src_h, job.width, job.height, job.fit)  # type: ignore[arg-type]
        cmd = ffmpeg.build_command(
            src=job.src,
            dst=job.dst,
            plan=plan,
            quality=job.quality,
            engine=job.engine,
            strip_metadata=job.strip_metadata,
            overwrite=job.overwrite,
            ffmpeg_path=job.ffmpeg_path,
        )
        job.dst.parent.mkdir(parents=True, exist_ok=True)

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            msg = (proc.stderr or "").strip() or f"ffmpeg exited with {proc.returncode}"
            return Result(job.src, None, ok=False, error=msg)
        return Result(job.src, job.dst, ok=True)

    except (FFmpegError, SizingError, OSError) as e:
        return Result(job.src, None, ok=False, error=f"{type(e).__name__}: {e}")


def run_batch(jobs: Iterable[Job], workers: int | None = None) -> list[Result]:
    jobs = list(jobs)
    if not jobs:
        return []
    if workers == 1 or len(jobs) == 1:
        return [run_job(j) for j in jobs]
    results: list[Result] = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(run_job, j) for j in jobs]
        for f in as_completed(futures):
            results.append(f.result())
    return results
