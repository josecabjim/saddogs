"""Print spider names for rescues missing today. One name per line."""

import sys
from datetime import date, datetime, timedelta, timezone

from saddogs_database.client import DatabaseClient
from spider_runner import load_spiders

STALE_DAYS = 7


def _known_rescue_pairs() -> dict[str, tuple[str, str]]:
    # Only BaseRescueSpider subclasses have rescue_name + island
    known_pairs_by_spider: dict[str, tuple[str, str]] = {}
    for cls in load_spiders():
        rescue_name = getattr(cls, "rescue_name", None)
        island = getattr(cls, "island", None)
        spider_name = getattr(cls, "name", None)
        if rescue_name and island and spider_name:
            known_pairs_by_spider[spider_name] = (rescue_name, island)
    return known_pairs_by_spider


def _to_date(value) -> date:
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    if hasattr(value, "date"):
        return value.date()
    raise ValueError(f"Unrecognized date value: {value!r}")


def census_missing(db: DatabaseClient) -> bool:
    latest = db.census.get_latest()
    if not latest:
        return True

    created_at = latest.get("created_at")
    if isinstance(created_at, str):
        entry_date = created_at[:10]
    elif hasattr(created_at, "date"):
        entry_date = created_at.date().isoformat()
    else:
        entry_date = ""

    return entry_date != date.today().isoformat()


def get_missing_spider_names() -> list[str]:
    known_pairs_by_spider = _known_rescue_pairs()

    if not known_pairs_by_spider:
        return []

    db = DatabaseClient()
    missing_pairs = db.rescues.get_rescues_missing_for_date(
        known_pairs=list(known_pairs_by_spider.values())
    )
    missing_set = set(missing_pairs)

    missing = [
        spider_name
        for spider_name, pair in known_pairs_by_spider.items()
        if pair in missing_set
    ]

    if census_missing(db):
        missing.append("census")

    return missing


def get_stale_spider_names(stale_days: int = STALE_DAYS) -> list[str]:
    """Spider names (plus 'census') whose most recent non-flagged row is
    stale_days+ old, or that have no clean row at all. This is a different,
    worse bar than get_missing_spider_names()'s "missing today"."""
    known_pairs_by_spider = _known_rescue_pairs()
    if not known_pairs_by_spider:
        return []

    db = DatabaseClient()
    latest_by_pair = db.rescues.get_latest_clean_dates()
    today = date.today()

    stale = [
        spider_name
        for spider_name, pair in known_pairs_by_spider.items()
        if pair not in latest_by_pair
        or (today - _to_date(latest_by_pair[pair])).days >= stale_days
    ]

    census_latest = db.census.get_latest_clean()
    if not census_latest or (
        today - _to_date(census_latest["created_at"])
    ).days >= stale_days:
        stale.append("census")

    return stale


def get_recent_needs_review() -> tuple[list[dict], list[dict]]:
    """(rescue rows, census rows) flagged needs_review in the last 24h."""
    db = DatabaseClient()
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return db.rescues.get_recent_needs_review(since), db.census.get_recent_needs_review(
        since
    )


if __name__ == "__main__":
    missing = get_missing_spider_names()
    if not missing:
        print("__none__")
        sys.exit(0)
    for name in missing:
        print(name)
