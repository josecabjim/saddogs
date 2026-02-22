import os

import scrapy
import datetime
from supabase import create_client

# TODO mapping should be in a config file
mapping = {
    "No Canario": "no_canario",
    "El Hierro": "el_hierro",
    "Fuerteventura": "fuerteventura",
    "Gran Canaria": "gran_canaria",
    "La Gomera": "la_gomera",
    "La Palma": "la_palma",
    "Lanzarote": "lanzarote",
    "Tenerife": "tenerife",
}


def str_to_int(s: str) -> int:
    s = s.replace(".", "")
    return int(s)


class CensusSpider(scrapy.Spider):
    name = "census"
    start_urls = ["https://www.zoocan.net/Paginas/Censos.aspx"]

    def __init__(self):
        self.table_key_islands = "Islas"
        self.table_key_dogs = "Perros"

        # TODO use separate database module
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.supabase = create_client(url, key)

    def parse_header(self, response) -> list[str]:
        header_top = response.css("table thead th span::text").get()
        header_rest = response.css("table thead th::text").getall()
        header = [header_top] + header_rest

        if self.table_key_islands not in header:
            raise ValueError(
                f"islands_table_key: {self.table_key_islands} not found in table header"
            )
        if self.table_key_dogs not in header:
            raise ValueError(
                f"dog_table_key: {self.table_key_dogs} not found in table header"
            )

        return header

    def parse(self, response):
        header = self.parse_header(response)
        table_content = response.css("table tbody td::text").getall()

        len_header = len(header)
        table = {h: [] for h in header}

        for i, col in enumerate(table_content):
            row = divmod(i, len_header)[1]
            table[header[row]].append(col)

        islands = table[self.table_key_islands]
        dogs = table[self.table_key_dogs]

        date = dict(
            year=datetime.date.today().year,
            month=datetime.date.today().month,
            day=datetime.date.today().day,
        )
        data_census = {island: n for island, n in zip(islands, dogs)}
        data_db = {
            key_db: str_to_int(data_census[key_census])
            for key_census, key_db in mapping.items()
        }

        # TODO change date format?
        data = dict(**data_db, **date)

        # TODO use separate database module
        try:
            response = (
                self.supabase.table("census")
                .upsert(data, on_conflict="year,month,day")
                .execute()
            )

            self.logger.info(f"Upsert successful: {response.data}")

        except Exception as e:
            self.logger.error(f"Upsert failed: {e}")
            raise
