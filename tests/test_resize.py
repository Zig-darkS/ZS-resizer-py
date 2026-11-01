"""FFmpeg command construction and pipeline edge-case tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from zs_resizer import ffmpeg
from zs_resizer.cli import _output_path
from zs_resizer.errors import FFmpegError
from zs_resizer.ffmpeg import FFmpegInfo
from zs_resizer.pipeline import Job, run_job
from zs_resizer.sizing import compute_plan


FAKE_INFO = FFmpegInfo(
    path="/usr/bin/ffmpeg",
    version="ffmpeg version 6.1.1",
    has_zscale=True,
    encoders=frozenset({"mjpeg", "libwebp", "libaom-av1", "libsvtav1"}),
)

NO_ZSCALE = FFmpegInfo(
    path="/usr/bin/ffmpeg",
    version="ffmpeg version 5.0",
    has_zscale=False,
    encoders=frozenset({"mjpeg", "libwebp"}),
)


# --- quality_args --------------------------------------------------------


@pytest.mark.parametrize(
    "quality,expected_qv",
    [(1, "31"), (50, "17"), (100, "2")],
)
def test_quality_jpeg_maps_high_quality_low_qv(quality: int, expected_qv: str) -> None:
    assert ffmpeg.quality_args("jpg", quality) == ["-q:v", expected_qv]


def test_quality_clamps_out_of_range() -> None:
    assert ffmpeg.quality_args("jpg", 0) == ffmpeg.quality_args("jpg", 1)
    assert ffmpeg.quality_args("jpg", 999) == ffmpeg.quality_args("jpg", 100)


def test_quality_webp_passthrough() -> None:
    assert ffmpeg.quality_args("webp", 82) == ["-quality", "82"]


def test_quality_png_is_lossless() -> None:
    assert ffmpeg.quality_args("png", 90) == ["-compression_level", "9"]


def test_quality_avif_high_quality_means_low_crf() -> None:
    low = int(ffmpeg.quality_args("avif", 1)[1])
    high = int(ffmpeg.quality_args("avif", 100)[1])
    assert low > high


def test_quality_unknown_format_is_empty() -> None:
    assert ffmpeg.quality_args("bmp", 90) == []


# --- build_command -------------------------------------------------------


def _vf(cmd: list[str]) -> str:
    return cmd[cmd.index("-vf") + 1]


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_inside_uses_zscale(_p) -> None:
    plan = compute_plan(1920, 1080, 800, 800, "inside")
    cmd = ffmpeg.build_command(src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan)
    vf = _vf(cmd)
    assert vf.startswith("zscale=")
    assert "w=800" in vf and "h=450" in vf
    assert "crop=" not in vf and "pad=" not in vf


@patch.object(ffmpeg, "probe", return_value=NO_ZSCALE)
def test_build_auto_falls_back_to_swscale(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    cmd = ffmpeg.build_command(src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan)
    assert _vf(cmd).startswith("scale=")
    assert "flags=lanczos" in _vf(cmd)


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_engine_swscale_forces_scale(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    cmd = ffmpeg.build_command(
        src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan, engine="swscale"
    )
    assert _vf(cmd).startswith("scale=")


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_cover_appends_crop(_p) -> None:
    plan = compute_plan(1920, 1080, 500, 500, "cover")
    cmd = ffmpeg.build_command(src=Path("a.png"), dst=Path("b.png"), plan=plan)
    assert "crop=" in _vf(cmd)


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_pad_appends_pad(_p) -> None:
    plan = compute_plan(1920, 1080, 500, 500, "pad")
    cmd = ffmpeg.build_command(src=Path("a.png"), dst=Path("b.png"), plan=plan)
    assert "pad=" in _vf(cmd)


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_no_overwrite_uses_n(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    cmd = ffmpeg.build_command(src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan)
    assert "-n" in cmd and "-y" not in cmd


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_overwrite_uses_y(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    cmd = ffmpeg.build_command(
        src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan, overwrite=True
    )
    assert "-y" in cmd and "-n" not in cmd


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_strip_metadata(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    cmd = ffmpeg.build_command(
        src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan, strip_metadata=True
    )
    i = cmd.index("-map_metadata")
    assert cmd[i + 1] == "-1"


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_ends_with_dst(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    dst = Path("out") / "b.jpg"
    cmd = ffmpeg.build_command(src=Path("a.jpg"), dst=dst, plan=plan)
    assert cmd[-1] == str(dst)


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_rejects_missing_extension(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    with pytest.raises(FFmpegError):
        ffmpeg.build_command(src=Path("a.jpg"), dst=Path("no_ext"), plan=plan)


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_applies_format_specific_quality(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    jpg = ffmpeg.build_command(
        src=Path("a.jpg"), dst=Path("b.jpg"), plan=plan, quality=50
    )
    assert "-q:v" in jpg
    webp = ffmpeg.build_command(
        src=Path("a.jpg"), dst=Path("b.webp"), plan=plan, quality=50
    )
    assert "-quality" in webp


# --- cli._output_path ----------------------------------------------------


def _ns(**kw) -> argparse.Namespace:
    defaults = dict(output=None, output_dir=None, suffix="")
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def test_output_default_suffix_avoids_clobber() -> None:
    dst = _output_path(Path("photo.jpg"), _ns(), single=True)
    assert dst.name == "photo_resized.jpg"


def test_output_dir_no_suffix() -> None:
    dst = _output_path(Path("photo.jpg"), _ns(output_dir="out"), single=True)
    assert dst == Path("out") / "photo.jpg"


def test_output_suffix_only() -> None:
    dst = _output_path(Path("photo.jpg"), _ns(suffix="_sm"), single=True)
    assert dst.name == "photo_sm.jpg"


def test_output_path_only_single() -> None:
    with pytest.raises(SystemExit):
        _output_path(Path("photo.jpg"), _ns(output="x.jpg"), single=False)


def test_output_refuses_same_as_source() -> None:
    src = Path("photo.jpg")
    with pytest.raises(SystemExit):
        _output_path(src, _ns(output_dir="."), single=True)


# --- pipeline.run_job early returns --------------------------------------


def test_run_job_rejects_same_src_dst() -> None:
    p = Path("same.jpg")
    job = Job(src=p, dst=p, width=100)
    res = run_job(job)
    assert not res.ok
    assert "same file" in (res.error or "")


def test_run_job_rejects_existing_dst(tmp_path: Path) -> None:
    src = tmp_path / "a.jpg"
    src.write_bytes(b"fake")
    dst = tmp_path / "b.jpg"
    dst.write_bytes(b"existing")
    job = Job(src=src, dst=dst, width=100, overwrite=False)
    res = run_job(job)
    assert not res.ok
    assert "exists" in (res.error or "")

NO_AV1 = FFmpegInfo(
    path="/usr/bin/ffmpeg",
    version="ffmpeg version 5.0",
    has_zscale=False,
    encoders=frozenset({"mjpeg", "libwebp"}),
)


@patch.object(ffmpeg, "probe", return_value=NO_AV1)
def test_build_avif_without_encoder_raises(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    with pytest.raises(FFmpegError, match="AV1 encoder"):
        ffmpeg.build_command(src=Path("a.jpg"), dst=Path("b.avif"), plan=plan)


@patch.object(ffmpeg, "probe", return_value=FAKE_INFO)
def test_build_avif_picks_encoder(_p) -> None:
    plan = compute_plan(100, 100, 50, 50)
    cmd = ffmpeg.build_command(src=Path("a.jpg"), dst=Path("b.avif"), plan=plan)
    i = cmd.index("-c:v")
    assert cmd[i + 1] in ("libsvtav1", "libaom-av1")
