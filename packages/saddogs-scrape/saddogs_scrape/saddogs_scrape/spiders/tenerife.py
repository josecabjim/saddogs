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


class TenerifeRefugioInternacional(scrapy.Spider):
    name = "tenerife_refugio_internacional"
    start_urls = ["https://refugiodeanimales.org/adopta/"]

    def __init__(self, *args, **kwargs):
        super(TenerifeRefugioInternacional, self).__init__(*args, **kwargs)

        # Initialize Supabase client using environment variables
        # Note: Ensure these are set in your local environment or .env file
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError(
                "Supabase URL or Service Role Key missing from environment."
            )

        self.supabase = create_client(url, key)
        self.total_count = 0

    def parse(self, response):
        # Select only the adoption images
        items = response.css('img[width="1080"][height="675"]')
        page_count = len(items)

        self.total_count += page_count

        self.logger.info(
            f"Page {response.url} -> {page_count} items (total: {self.total_count})"
        )

        # follow next page if it exists
        next_page = response.css("a.next.page-numbers::attr(href)").get()

        if next_page:
            yield response.follow(next_page, callback=self.parse)
        else:
            # No more pages -> save to database and return final count
            data_db = {
                "total_dogs": self.total_count,
                "rescue_name": "Refugio Internacional para Animales",
                "island": "Tenerife",
            }

            # Insert into your specific table (replace 'dogs_count' with your actual table name)
            try:
                db_response = self.supabase.table("rescues").insert(data_db).execute()
                self.logger.info(
                    f"Data successfully saved to Supabase: {db_response.data}"
                )

                # Also yield the item for Scrapy's internal tracking
                yield data_db

            except Exception as e:
                self.logger.error(f"Failed to insert data into Supabase: {e}")


class TenerifeValleColino(scrapy.Spider):
    name = "tenerife_valle_colino"
    start_urls = ["https://www.alberguevallecolino.org/adoptar/perros"]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, *args, **kwargs):
        super(TenerifeValleColino, self).__init__(*args, **kwargs)

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
        text = response.css("div.col-sm-6.text-right::text").get()

        if not text:
            self.logger.warning("Could not find the pagination text")
            return

        # Example text:
        # "Mostrando 1 a 12 de 105 (9 Páginas)"
        match = re.search(r"de\s+(\d+)", text)

        total = int(match.group(1)) if match else None

        data_db = {
            "total_dogs": total,
            "rescue_name": "Albergue Valle Colino",
            "island": "Tenerife",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")


class TenerifeAdejeMascotas(scrapy.Spider):
    name = "tenerife_adeje_mascotas"
    start_urls = ["https://www.adeje.es/mascotas/mascotas-en-adopcion"]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, *args, **kwargs):
        super(TenerifeAdejeMascotas, self).__init__(*args, **kwargs)

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
        # Count each animal card
        items = response.css("div.ListadoImgItem")
        count = len(items)

        self.logger.info(f"Found {count} animals")

        data_db = {
            "total_dogs": count,
            "rescue_name": "Adeje Mascotas",
            "island": "Tenerife",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")


class TenerifeTierraBlanca(scrapy.Spider):
    name = "tenerife_tierra_blanca"
    start_urls = ["https://cpatierrablanca.es/es/adopcion/perros-en-adopcion.html"]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, *args, **kwargs):
        super(TenerifeTierraBlanca, self).__init__(*args, **kwargs)

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
        # Extract the pagination text
        text = response.css("span.fc_item_total_data::text").get()

        if not text:
            self.logger.warning("Pagination text not found")
            return

        text = text.strip()

        # Example:
        # "Resultados 1 - 10 de 182"
        match = re.search(r"de\s+(\d+)", text)

        total = int(match.group(1)) if match else None

        data_db = {
            "total_dogs": total,
            "rescue_name": "CPA Tierra Blanca",
            "island": "Tenerife",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")
