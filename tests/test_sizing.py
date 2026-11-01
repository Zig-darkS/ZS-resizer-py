import pytest

from zs_resizer.errors import SizingError
from zs_resizer.sizing import compute_plan


def test_inside_wide():
    p = compute_plan(1920, 1080, 800, 800, "inside")
    assert (p.out_width, p.out_height) == (800, 450)


def test_inside_tall():
    p = compute_plan(1080, 1920, 800, 800, "inside")
    assert (p.out_width, p.out_height) == (450, 800)


def test_only_width():
    p = compute_plan(1920, 1080, 800, None, "inside")
    assert (p.out_width, p.out_height) == (800, 450)


def test_only_height():
    p = compute_plan(1920, 1080, None, 540, "inside")
    assert (p.out_width, p.out_height) == (960, 540)


def test_fill():
    p = compute_plan(1920, 1080, 500, 500, "fill")
    assert (p.out_width, p.out_height) == (500, 500)
    assert (p.scale_width, p.scale_height) == (500, 500)


def test_cover():
    p = compute_plan(1920, 1080, 500, 500, "cover")
    assert (p.out_width, p.out_height) == (500, 500)
    assert p.scale_width >= 500 and p.scale_height >= 500
    assert p.crop is True


def test_pad():
    p = compute_plan(1920, 1080, 500, 500, "pad")
    assert (p.out_width, p.out_height) == (500, 500)
    assert (p.scale_width, p.scale_height) == (500, 281)
    assert p.pad is True


def test_no_dims():
    with pytest.raises(SizingError):
        compute_plan(100, 100, None, None)


def test_bad_source():
    with pytest.raises(SizingError):
        compute_plan(0, 100, 50, None)


def test_bad_target():
    with pytest.raises(SizingError):
        compute_plan(100, 100, -1, None)
