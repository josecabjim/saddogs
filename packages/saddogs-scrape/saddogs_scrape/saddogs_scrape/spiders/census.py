from __future__ import annotations

from typing import Dict

from saddogs_scrape.spiders.base.base_spider import BaseSpider
from saddogs_scrape.spiders.services.validation import validate_count


class CensusSpider(BaseSpider):
    name = "census"
    start_urls = ["https://www.zoocan.net/Paginas/Censos.aspx"]
    db_table = "census"

    table_selector = "table"
    header_selector = "thead th::text"
    cell_selector = "tbody td::text"

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.db_table:
            raise ValueError(f"{self.name}: db_table must be defined")

    def get_previous_census(self):
        try:
            return self.db.census.get_latest()
        except Exception as e:
            self.logger.warning(f"Could not fetch previous census: {e}")
            return None

    def validate_census_data(self, data: Dict[str, int]):
        """Validate that each island count is a positive integer."""
        for island, count in data.items():
            if not isinstance(count, int) or count < 0:
                raise ValueError(
                    f"{self.name}: Invalid count for {island}: {count} (expected positive int)"
                )

    # TODO should move to database
    def validate_against_previous_census(self, previous: Dict, current: Dict[str, int]):
        """Validate current census against previous to detect anomalies."""
        if not previous:
            return  # No previous data to validate against

        for island, current_count in current.items():
            previous_count = previous.get(island)
            if previous_count is None:
                continue

            # Check for drastic drops (more than 50% decrease)
            if current_count < previous_count * 0.5:
                raise ValueError(
                    f"{self.name}: Anomaly detected in {island}: count dropped from {previous_count} to {current_count}"
                )

            # Check for extreme increases (more than 200% increase)
            if current_count > previous_count * 3:
                raise ValueError(
                    f"{self.name}: Anomaly detected in {island}: count jumped from {previous_count} to {current_count}"
                )

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

    def save_result(self, data):
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would upsert data: {data}")
        else:
            self.db.census.save(data)
            self.logger.info("Upsert successful")

        return data

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

        # Validate the census data
        self.validate_census_data(data_db)

        # Validate against previous census
        previous = self.get_previous_census()
        self.validate_against_previous_census(previous, data_db)

        self.save_result(data_db)
        yield data_db
