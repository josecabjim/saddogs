import os

import scrapy
from saddogs_database.client import DatabaseClient
from spiders.services.validation import validate_against_previous, validate_count


class BaseSpider(scrapy.Spider):
    def __init__(self, *args, dry_run=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.dry_run = dry_run

        if not self.dry_run:
            self.db = DatabaseClient()

        self.total_count = 0


class BaseRescueSpider(BaseSpider):
    rescue_name = None
    island = None

    def get_previous_count(self):
        try:
            return self.db.rescues.get_latest_count(self.rescue_name, self.island)
        except Exception as e:
            self.logger.warning(f"Could not fetch previous count: {e}")
            return None

    def save_result(self, count):
        if count <= 0:
            self.logger.warning(f"Got zero count, skipping save")
            return  # yields nothing → item_scraped_count stays 0 → monitor retries it

        validate_count(self.name, count)

        previous = self.get_previous_count()

        needs_review = validate_against_previous(self.name, previous, count)
        if needs_review:
            self.logger.warning(
                f"{self.name}: flagging for review (previous={previous}, current={count})"
            )

        data = {
            "rescue_name": self.rescue_name,
            "island": self.island,
            "total_dogs": count,
            "needs_review": needs_review,
        }

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would save result: {data}")
        else:
            self.db.rescues.save_count(
                self.rescue_name,
                self.island,
                count,
                needs_review=needs_review,
            )
            self.logger.info(f"Saved result: {data}")

        return data
