from __future__ import annotations

from typing import Dict

from saddogs_scrape.spiders.base.table_spider import BaseTableSpider


class CensusSpider(BaseTableSpider):
    name = "census"
    start_urls = ["https://www.zoocan.net/Paginas/Censos.aspx"]
    db_table = "census"

    islands_key = "Islas"
    dogs_key = "Perros"

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

    def parse_table(self, response) -> Dict[str, list[str]]:
        # Handle special case: first header cell is wrapped in <span>
        header_top = response.css("table thead th span::text").get()
        header_rest = response.css("table thead th::text").getall()
        header = [header_top] + header_rest

        if not header or not header[0]:
            raise ValueError(f"{self.name}: could not extract table header")

        cells = response.css("table tbody td::text").getall()
        if not cells:
            raise ValueError(f"{self.name}: could not extract table content")

        table = {h: [] for h in header}
        for i, cell in enumerate(cells):
            table[header[i % len(header)]].append(cell)

        return table

    def parse(self, response):
        table = self.parse_table(response)

        if self.islands_key not in table or self.dogs_key not in table:
            raise ValueError(f"{self.name}: missing required columns")

        islands = table[self.islands_key]
        dogs = table[self.dogs_key]

        if len(islands) != len(dogs):
            raise ValueError(f"{self.name}: column length mismatch")

        census = {i.strip(): d for i, d in zip(islands, dogs)}
        data_db = {}

        for label, db_key in self.mapping.items():
            if label in census:
                try:
                    data_db[db_key] = int(census[label].replace(".", "").strip())
                except ValueError as e:
                    raise ValueError(
                        f"{self.name}: could not parse '{label}': {census[label]!r}"
                    ) from e

        self.save(data_db)
