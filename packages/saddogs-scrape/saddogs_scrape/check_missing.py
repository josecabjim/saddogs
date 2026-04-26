"""Print spider names for rescues missing today. One name per line."""

import sys

from saddogs_database.client import DatabaseClient
from saddogs_scrape.spider_runner import load_spiders


def get_missing_spider_names() -> list[str]:
    all_spiders = load_spiders()

    # Only BaseRescueSpider subclasses have rescue_name + island
    known_pairs_by_spider: dict[str, tuple[str, str]] = {}
    for cls in all_spiders:
        rescue_name = getattr(cls, "rescue_name", None)
        island = getattr(cls, "island", None)
        spider_name = getattr(cls, "name", None)
        if rescue_name and island and spider_name:
            known_pairs_by_spider[spider_name] = (rescue_name, island)

    if not known_pairs_by_spider:
        return []

    db = DatabaseClient()
    missing_pairs = db.rescues.get_rescues_missing_for_date(
        known_pairs=list(known_pairs_by_spider.values())
    )
    missing_set = set(missing_pairs)

    return [
        spider_name
        for spider_name, pair in known_pairs_by_spider.items()
        if pair in missing_set
    ]


if __name__ == "__main__":
    missing = get_missing_spider_names()
    if not missing:
        print("__none__")
        sys.exit(0)
    for name in missing:
        print(name)
