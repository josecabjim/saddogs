"""Boundary tests for CensusSpider.validate_against_previous_census, the
census path's own anomaly check (separate implementation from
spiders/services/validation.py's validate_against_previous, used by the
rescue spiders). Instantiated with dry_run=True so no DatabaseClient / env
vars / network access is needed -- this is pure per-island threshold logic."""

import pytest
from spiders.census import CensusSpider


@pytest.fixture
def spider():
    return CensusSpider(dry_run=True)


class TestDropThreshold:
    def test_exactly_50_percent_drop_is_not_anomalous(self, spider):
        # current < previous * 0.5 is strict; the boundary itself (5 == 10*0.5)
        # is NOT flagged.
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 5}
        ) is False

    def test_just_over_50_percent_drop_is_anomalous(self, spider):
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 4}
        ) is True

    def test_just_under_50_percent_drop_is_not_anomalous(self, spider):
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 6}
        ) is False


class TestJumpThreshold:
    def test_exactly_3x_is_not_anomalous(self, spider):
        # current > previous * 3 is strict; the boundary itself (30 == 10*3)
        # is NOT flagged.
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 30}
        ) is False

    def test_just_over_3x_is_anomalous(self, spider):
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 31}
        ) is True

    def test_just_under_3x_is_not_anomalous(self, spider):
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 29}
        ) is False


class TestNoChangeAndMissingPrevious:
    def test_equal_values_is_not_anomalous(self, spider):
        assert spider.validate_against_previous_census(
            {"tenerife": 10}, {"tenerife": 10}
        ) is False

    def test_no_previous_row_at_all_is_not_anomalous(self, spider):
        # `previous` falsy (None, or an empty dict as get_latest() would
        # return for a brand-new table) short-circuits entirely.
        assert spider.validate_against_previous_census(
            None, {"tenerife": 10}
        ) is False
        assert spider.validate_against_previous_census(
            {}, {"tenerife": 10}
        ) is False

    def test_island_missing_from_previous_is_not_anomalous(self, spider):
        # previous.get(island) is None for an island with no prior value ->
        # skipped (continue), not flagged.
        assert spider.validate_against_previous_census(
            {"gran_canaria": 50}, {"tenerife": 999}
        ) is False

    def test_previous_zero_for_island_is_anomalous_on_any_increase(self, spider):
        # Unlike validate_against_previous (rescue path), this per-island
        # check has no previous_count == 0 guard: previous*3 == 0, so any
        # positive current count is ">" it and gets flagged. Documenting
        # this divergence explicitly since it's exactly the kind of subtle
        # cross-implementation inconsistency that could cause a surprise.
        assert spider.validate_against_previous_census(
            {"tenerife": 0}, {"tenerife": 5}
        ) is True

    def test_previous_zero_and_current_zero_is_not_anomalous(self, spider):
        assert spider.validate_against_previous_census(
            {"tenerife": 0}, {"tenerife": 0}
        ) is False


class TestMultiIsland:
    def test_one_anomalous_island_flags_whole_result(self, spider):
        previous = {"tenerife": 100, "la_palma": 20}
        current = {"tenerife": 100, "la_palma": 1}  # la_palma: >50% drop
        assert spider.validate_against_previous_census(previous, current) is True

    def test_all_islands_within_bounds_is_not_anomalous(self, spider):
        previous = {"tenerife": 100, "la_palma": 20, "lanzarote": 50}
        current = {"tenerife": 110, "la_palma": 22, "lanzarote": 45}
        assert spider.validate_against_previous_census(previous, current) is False
