"""Tests for the pure date-handling helpers in check_missing.py.

This is deliberately the most important file in this test suite: a real
daily-summary incident falsely reported almost everything as "missing" due
to a date/timing edge case in exactly this kind of logic, and no test caught
it because none existed. These tests use plain strings/dicts/datetimes as
fixtures -- no Supabase connection, no mocking library, just small fake
stand-ins for the one `db` argument that needs one.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from check_missing import _to_date, census_missing


class TestToDate:
    def test_parses_plain_iso_date_string(self):
        assert _to_date("2026-10-04") == date(2026, 10, 4)

    def test_parses_iso_datetime_string_with_time_and_offset(self):
        # Supabase often returns full timestamps; only the first 10 chars
        # (the date portion) should be used.
        assert _to_date("2026-10-04T23:59:59+00:00") == date(2026, 10, 4)

    def test_parses_iso_datetime_string_with_z_suffix(self):
        assert _to_date("2026-01-31T00:00:00Z"[:10]) == date(2026, 1, 31)

    def test_accepts_datetime_like_object_with_date_method(self):
        # The real-world case: a row's created_at field deserialized as an
        # actual datetime object rather than a string.
        dt = datetime(2026, 10, 4, 12, 30, tzinfo=timezone.utc)
        assert _to_date(dt) == date(2026, 10, 4)

    def test_raises_on_unrecognized_value(self):
        with pytest.raises(ValueError):
            _to_date(12345)

    def test_raises_on_none(self):
        with pytest.raises(ValueError):
            _to_date(None)


class _FakeCensusRepo:
    def __init__(self, latest):
        self._latest = latest

    def get_latest(self):
        return self._latest


class _FakeDB:
    """Minimal stand-in for DatabaseClient exposing only what
    census_missing() touches (db.census.get_latest()). Not a mock of
    Supabase -- just a plain fixture object."""

    def __init__(self, latest):
        self.census = _FakeCensusRepo(latest)


class TestCensusMissing:
    def test_no_row_at_all_is_missing(self):
        db = _FakeDB(latest=None)
        assert census_missing(db) is True

    def test_empty_dict_is_missing(self):
        db = _FakeDB(latest={})
        assert census_missing(db) is True

    def test_todays_row_as_date_only_string_is_not_missing(self):
        today_str = date.today().isoformat()  # noqa: DTZ011 - matches census_missing()'s own naive date.today() comparison
        db = _FakeDB(latest={"created_at": today_str})
        assert census_missing(db) is False

    def test_todays_row_as_full_timestamp_string_is_not_missing(self):
        # This is the shape the real incident involved: a full timestamp
        # string whose first 10 chars are today's date but which is NOT
        # equal to date.today().isoformat() as a whole string.
        today_timestamp = (
            datetime.now(timezone.utc).strftime("%Y-%m-%d") + "T23:59:59.123456+00:00"
        )
        db = _FakeDB(latest={"created_at": today_timestamp})
        assert census_missing(db) is False

    def test_yesterdays_row_is_missing(self):
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()  # noqa: DTZ011 - matches census_missing()'s own naive date.today() comparison
        db = _FakeDB(latest={"created_at": yesterday_str})
        assert census_missing(db) is True

    def test_todays_row_as_datetime_object_is_not_missing(self):
        # The DB client may hand back a real datetime instead of a string.
        now = datetime.now(timezone.utc)
        db = _FakeDB(latest={"created_at": now})
        assert census_missing(db) is False

    def test_yesterdays_row_as_datetime_object_is_missing(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        db = _FakeDB(latest={"created_at": yesterday})
        assert census_missing(db) is True

    def test_missing_created_at_key_is_missing(self):
        db = _FakeDB(latest={"some_other_field": 1})
        assert census_missing(db) is True

    def test_unrecognized_created_at_type_is_missing(self):
        # Falls through to entry_date = "" which never equals today ->
        # fails safe as "missing" rather than silently matching.
        db = _FakeDB(latest={"created_at": 12345})
        assert census_missing(db) is True
