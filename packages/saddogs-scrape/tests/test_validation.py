"""Boundary tests for spiders/services/validation.py's anomaly check, used by
every rescue-count spider via BaseRescueSpider.save_result(). This is the kind
of pure threshold logic that, if subtly wrong, produces exactly the sort of
false "anomaly"/"missing" incident this test suite exists to catch early."""

import warnings

import pytest

from spiders.services.validation import validate_against_previous


def _call(previous, current):
    """Call validate_against_previous and capture whether it warned."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = validate_against_previous("some_spider", previous, current)
    return result, bool(caught)


class TestDropThreshold:
    """Flagged when current_count / previous_count < 0.5 (a >50% drop)."""

    def test_exactly_50_percent_drop_is_not_anomalous(self):
        # 5/10 == 0.5, the boundary itself is NOT flagged (strict <).
        result, warned = _call(previous=10, current=5)
        assert result is False
        assert not warned

    def test_just_over_50_percent_drop_is_anomalous(self):
        # 4/10 == 0.4 < 0.5 -> flagged.
        result, warned = _call(previous=10, current=4)
        assert result is True
        assert warned

    def test_just_under_50_percent_drop_is_not_anomalous(self):
        # 6/10 == 0.6, a 40% drop -> not flagged.
        result, warned = _call(previous=10, current=6)
        assert result is False
        assert not warned


class TestJumpThreshold:
    """Flagged when current_count / previous_count > 3 (a >200% jump)."""

    def test_exactly_3x_is_not_anomalous(self):
        # 30/10 == 3.0, the boundary itself is NOT flagged (strict >).
        result, warned = _call(previous=10, current=30)
        assert result is False
        assert not warned

    def test_just_over_3x_is_anomalous(self):
        result, warned = _call(previous=10, current=31)
        assert result is True
        assert warned

    def test_just_under_3x_is_not_anomalous(self):
        result, warned = _call(previous=10, current=29)
        assert result is False
        assert not warned


class TestNoChangeAndMissingPrevious:
    def test_equal_values_is_not_anomalous(self):
        result, warned = _call(previous=10, current=10)
        assert result is False
        assert not warned

    def test_previous_none_is_not_anomalous(self):
        # No prior row to compare against -> nothing to flag.
        result, warned = _call(previous=None, current=1000)
        assert result is False
        assert not warned

    def test_previous_zero_is_not_anomalous(self):
        # Division by zero is explicitly guarded against; a brand-new rescue
        # going from 0 to any count should never be flagged as a "jump".
        result, warned = _call(previous=0, current=500)
        assert result is False
        assert not warned

    def test_current_zero_against_nonzero_previous_is_anomalous(self):
        # 0/10 == 0.0 < 0.5 -> a drop to zero is flagged, not silently dropped.
        result, warned = _call(previous=10, current=0)
        assert result is True
        assert warned


@pytest.mark.parametrize(
    "previous,current,expected",
    [
        (1, 1, False),
        (100, 1, True),  # drop
        (1, 1000, True),  # jump
        (2, 7, True),  # 3.5x jump
        (2, 6, False),  # exactly 3x
    ],
)
def test_parametrized_boundaries(previous, current, expected):
    result, _ = _call(previous, current)
    assert result is expected
