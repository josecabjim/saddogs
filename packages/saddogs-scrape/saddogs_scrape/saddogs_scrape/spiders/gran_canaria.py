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


class GranCanariaBanaderos(scrapy.Spider):
    name = "gran_canaria_banaderos"
    # Target the iframe source directly to bypass the parent page
    start_urls = ["https://albergueanimalesgrancanaria.com/Nuestros-Animales"]

    custom_settings = {"ROBOTSTXT_OBEY": False}

    def __init__(self, *args, **kwargs):
        super(GranCanariaBanaderos, self).__init__(*args, **kwargs)

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
            "rescue_name": "Banaderos",
            "island": "Gran Canaria",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")


class GranCanariaTelde(scrapy.Spider):
    name = "gran_canaria_telde"
    # Target the iframe source directly to bypass the parent page
    start_urls = ["https://albergueanimalestelde.com/Nuestros-Animales"]

    custom_settings = {"ROBOTSTXT_OBEY": False}

    def __init__(self, *args, **kwargs):
        super(GranCanariaTelde, self).__init__(*args, **kwargs)

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
            "rescue_name": "Telde",
            "island": "Gran Canaria",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")


class GranCanariaSosHunde(scrapy.Spider):
    name = "gran_canaria_sos_hunde"
    start_urls = ["https://www.sos-hunde-gc.com/vermittlung"]

    def __init__(self, *args, **kwargs):
        super(GranCanariaSosHunde, self).__init__(*args, **kwargs)

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
        # Count all elements: <div role="listitem" class="_FiCX">
        items = response.css('div[role="listitem"]._FiCX')
        total_dogs = len(items)

        data_db = {
            "total_dogs": total_dogs,
            "rescue_name": "SOS Hunde",
            "island": "Gran Canaria",
        }

        # Insert into your specific table (replace 'dogs_count' with your actual table name)
        try:
            db_response = self.supabase.table("rescues").insert(data_db).execute()
            self.logger.info(f"Data successfully saved to Supabase: {db_response.data}")

            # Also yield the item for Scrapy's internal tracking
            yield data_db

        except Exception as e:
            self.logger.error(f"Failed to insert data into Supabase: {e}")


class GranCanariaAda(scrapy.Spider):
    name = "gran_canaria_ada"
    start_urls = ["https://www.adagrancanaria.org/pet-category/perros/"]

    def __init__(self, *args, **kwargs):
        super(GranCanariaAda, self).__init__(*args, **kwargs)

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
        # Count only real items (exclude placeholders)
        items = response.css("div.item:not(.item_placeholder)")
        page_count = len(items)

        self.total_count += page_count

        self.logger.info(
            f"Page {response.url} -> {page_count} items (total so far: {self.total_count})"
        )

        # Follow next page if it exists
        next_page = response.css("a.next.page-numbers::attr(href)").get()

        if next_page:
            yield response.follow(next_page, callback=self.parse)
        else:
            # No more pages -> save to database and return final count
            data_db = {
                "total_dogs": self.total_count,
                "rescue_name": "ADA Gran Canaria",
                "island": "Gran Canaria",
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
