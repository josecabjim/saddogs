import json
import os
import random
import re
import scrapy
from scrapy import Selector

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


class FuerteventuraCentroSur(scrapy.Spider):
    name = "fuerteventura_centro_sur"
    start_urls = ["https://mancomunidadcentrosurftv.org/adopciones/"]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, *args, **kwargs):
        super(FuerteventuraCentroSur, self).__init__(*args, **kwargs)

        # Initialize Supabase client using environment variables
        # Note: Ensure these are set in your local environment or .env file
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError(
                "Supabase URL or Service Role Key missing from environment."
            )

        self.supabase = create_client(url, key)

    def parse(self, response):
        # Count animal cards
        items = response.css("div.ficha-animal")
        count = len(items)

        self.logger.info(f"Found {count} animals")

        data_db = {
            "total_dogs": count,
            "rescue_name": "Mancomunidad Centro Sur Fuerteventura",
            "island": "Fuerteventura",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")


class FuerteventuraDogRescue(scrapy.Spider):
    name = "fuerteventura_dog_rescue"
    start_urls = ["https://www.fuerteventuradogrescue.org/es/perros/"]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, *args, **kwargs):
        super(FuerteventuraDogRescue, self).__init__(*args, **kwargs)

        # Initialize Supabase client using environment variables
        # Note: Ensure these are set in your local environment or .env file
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError(
                "Supabase URL or Service Role Key missing from environment."
            )

        self.supabase = create_client(url, key)

    def parse(self, response):
        # Only columns that actually contain a dog entry
        items = response.css(
            "div.wp-block-column.is-layout-flow.wp-block-column-is-layout-flow:has(h6.wp-block-heading)"
        )

        count = len(items)

        self.logger.info(f"Found {count} dogs")

        data_db = {
            "total_dogs": count,
            "rescue_name": "Fuerteventura Dog Rescue",
            "island": "Fuerteventura",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")
