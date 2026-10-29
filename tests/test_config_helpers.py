import pytest

from app.config import _roi


def test_roi_parser() -> None:
    assert _roi("0,0;1,0;1,1;0,1") == (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    )


def test_roi_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        _roi("0,0;2,0;1,1")
