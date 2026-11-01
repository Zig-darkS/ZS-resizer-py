"""Pure dimension math. No I/O, no FFmpeg."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import SizingError

Fit = Literal["inside", "cover", "fill", "pad"]


@dataclass(frozen=True, slots=True)
class ResizePlan:
    """How to get from source to output.

    scale_*  — intermediate dimensions passed to the scale filter.
    out_*    — final output dimensions.
    crop/pad — whether a second filter stage is required.
    """

    out_width: int
    out_height: int
    scale_width: int
    scale_height: int
    crop: bool = False
    pad: bool = False


def _round(x: float) -> int:
    return max(1, int(round(x)))


def compute_plan(
    src_w: int,
    src_h: int,
    width: int | None,
    height: int | None,
    fit: Fit = "inside",
) -> ResizePlan:
    if src_w <= 0 or src_h <= 0:
        raise SizingError(f"invalid source size {src_w}x{src_h}")
    if width is None and height is None:
        raise SizingError("at least one of --width/--height is required")
    if width is not None and width <= 0:
        raise SizingError(f"--width must be > 0, got {width}")
    if height is not None and height <= 0:
        raise SizingError(f"--height must be > 0, got {height}")

    ar = src_w / src_h

    # Single constraint: fit mode is irrelevant, other side follows aspect ratio.
    if width is None:
        w = _round(height * ar)
        return ResizePlan(w, height, w, height)
    if height is None:
        h = _round(width / ar)
        return ResizePlan(width, h, width, h)

    W, H = width, height

    if fit == "fill":
        return ResizePlan(W, H, W, H)

    if fit == "inside":
        sw, sh = W, _round(W / ar)
        if sh > H:
            sw, sh = _round(H * ar), H
        return ResizePlan(sw, sh, sw, sh)

    if fit == "pad":
        sw, sh = W, _round(W / ar)
        if sh > H:
            sw, sh = _round(H * ar), H
        return ResizePlan(W, H, sw, sh, pad=True)

    if fit == "cover":
        sw, sh = W, _round(W / ar)
        if sh < H:
            sw, sh = _round(H * ar), H
        return ResizePlan(W, H, sw, sh, crop=True)

    raise SizingError(f"unknown fit mode: {fit!r}")
