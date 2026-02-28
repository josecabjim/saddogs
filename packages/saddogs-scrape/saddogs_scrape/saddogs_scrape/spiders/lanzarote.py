import os
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


class LanzaroteTeguise(scrapy.Spider):
    name = "lanzarote_teguise"
    # Target the iframe source directly to bypass the parent page
    start_urls = ["https://albergueanimalesteguise.com/Nuestros-Animales"]

    custom_settings = {"ROBOTSTXT_OBEY": False}

    def __init__(self, *args, **kwargs):
        super(LanzaroteTeguise, self).__init__(*args, **kwargs)

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
        # Extract hidden fields for ASP.NET form
        formdata = {
            "ScriptManager": "ScriptManager|dnn$ctr383$View$lnkSearch",
            "dnn$dnnSearch2$txtSearch": "",
            "dnn$ctr383$View$chkPerro": "on",
            "dnn$ctr383$View$num_resultados": "19",
            "dnn$ctr383$View$pagina_actual": "1",
            "ScrollTop": "0",
            "__dnnVariable": response.css(
                "input[name='__dnnVariable']::attr(value)"
            ).get(),
            "__RequestVerificationToken": response.css(
                "input[name='__RequestVerificationToken']::attr(value)"
            ).get(),
            "__EVENTTARGET": "dnn$ctr383$View$lnkSearch",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": response.css("input[name='__VIEWSTATE']::attr(value)").get(),
            "__VIEWSTATEGENERATOR": response.css(
                "input[name='__VIEWSTATEGENERATOR']::attr(value)"
            ).get(),
            "__EVENTVALIDATION": response.css(
                "input[name='__EVENTVALIDATION']::attr(value)"
            ).get(),
            "__VIEWSTATEENCRYPTED": "",
            "__ASYNCPOST": "true",
        }

        yield scrapy.FormRequest(
            url=response.url,
            formdata=formdata,
            callback=self.parse_results,
            headers={
                "X-MicrosoftAjax": "Delta=true",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": response.url,
            },
        )

    def parse_results(self, response):
        # ASP.NET async responses are pipe-delimited
        # The HTML fragment is after the last pipe (|) in the updatePanel section
        body = response.text

        # Split the response by pipe
        parts = body.split("|")
        for part in parts:
            if "dnn_ctr383_View_lblTotal" in part:
                html_fragment = part
                break

        # Use Selector to parse the HTML fragment
        sel = Selector(text=html_fragment)
        total_text = sel.css("span#dnn_ctr383_View_lblTotal::text").get()

        # Convert to integer if needed
        total_dogs = int(total_text) if total_text else None

        data_db = {
            "total_dogs": total_dogs,
            "rescue_name": "Teguise",
            "island": "Lanzarote",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")
