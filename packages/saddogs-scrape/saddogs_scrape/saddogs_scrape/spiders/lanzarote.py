import scrapy
import datetime

class SaraSpider(scrapy.Spider):
    name = "lanzarote-sara"
    start_urls = ["https://saraprotectora.org/en/our-animals/find-a-dog/"]

    def __init__(self):
        self.table_key_islands = "Islas"
        self.table_key_dogs = "Perros"

    def parse_header(self, response) -> list[str]:
        header_top = response.css("table thead th span::text").get()
        header_rest = response.css("table thead th::text").getall()
        header = [header_top] + header_rest

        if self.table_key_islands not in header:
            raise ValueError(f"islands_table_key: {self.table_key_islands} not found in table header")
        if self.table_key_dogs not in header:
            raise ValueError(f"dog_table_key: {self.table_key_dogs} not found in table header")
        
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
            day=datetime.date.today().day
        )
        census_data = {island: n for island, n in zip(islands, dogs)}

        data = dict(
            date=date,
            data=census_data
        )

        yield data