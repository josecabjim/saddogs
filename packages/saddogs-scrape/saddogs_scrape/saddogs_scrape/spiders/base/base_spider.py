import os

import scrapy
from saddogs_scrape.spiders.services.validation import (
    validate_against_previous,
    validate_count,
)
from supabase import create_client


def get_supabase_client():
    """Return a Supabase client initialized from environment variables.

    Raises ValueError if required env vars are missing.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("Supabase URL or Service Role Key missing from environment.")

    return create_client(url, key)


def save_rescue_result(client, data):
    return client.table("rescues").insert(data).execute()


class BaseRescueSpider(scrapy.Spider):
    rescue_name = None
    island = None

    def __init__(self, *args, dry_run=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.dry_run = dry_run

        if not self.dry_run:
            self.supabase = get_supabase_client()

        self.total_count = 0

    def get_previous_count(self):

        try:
            response = (
                self.supabase.table("rescues")
                .select("total_dogs")
                .eq("rescue_name", self.rescue_name)
                .eq("island", self.island)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            data = response.data

            if not data:
                return None

            return data[0]["total_dogs"]

        except Exception as e:
            self.logger.warning(f"Could not fetch previous count: {e}")
            return None

    def save_result(self, count):

        validate_count(self.name, count)

        previous = self.get_previous_count()

        try:
            validate_against_previous(self.name, previous, count)
        except ValueError as e:
            self.logger.error(str(e))
            raise

        data = {
            "rescue_name": self.rescue_name,
            "island": self.island,
            "total_dogs": count,
        }

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would save result: {data}")
        else:
            save_rescue_result(self.supabase, data)
            self.logger.info(f"Saved result: {data}")

        return data


class CountSpider(BaseRescueSpider):
    selector = None
    pagination_selector = None

    def parse(self, response):

        items = response.css(self.selector)
        page_count = len(items)

        self.total_count += page_count

        next_page = None

        if self.pagination_selector:
            next_page = response.css(self.pagination_selector).get()

        if next_page:
            yield response.follow(next_page, callback=self.parse)
        else:
            yield self.save_result(self.total_count)
