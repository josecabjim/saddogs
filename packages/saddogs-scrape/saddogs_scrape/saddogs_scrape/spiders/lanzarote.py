import os
import scrapy
from supabase import create_client


class LanzaroteSaraSpider(scrapy.Spider):
    name = "lanzarote_sara"
    # Target the iframe source directly to bypass the parent page
    start_urls = ["https://animales.saraprotectora.org/animales/categoria/1"]

    def __init__(self, *args, **kwargs):
        super(LanzaroteSaraSpider, self).__init__(*args, **kwargs)

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
        # Extract the "XX animales" text
        raw_text = response.css("small::text").get()

        if raw_text:
            # Clean text: remove "animales" and whitespace to get the integer
            try:
                count_str = raw_text.replace("animales", "").strip()
                total_dogs = int(count_str)
            except ValueError:
                self.logger.error(f"Could not convert text to integer: {raw_text}")
                return

            # Prepare data for Supabase
            # created_at is usually handled automatically by Supabase defaults,
            # but we include the other requested columns here.
            data_db = {
                "total_dogs": total_dogs,
                "rescue_name": "Sara",
                "island": "Lanzarote",
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
