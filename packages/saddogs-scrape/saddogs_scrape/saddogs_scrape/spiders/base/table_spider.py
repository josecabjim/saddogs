from saddogs_scrape.spiders.base.base_spider import BaseRescueSpider


class BaseTableSpider(BaseRescueSpider):
    table_selector = "table"
    header_selector = "thead th::text"
    cell_selector = "tbody td::text"

    db_table = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.db_table:
            raise ValueError(f"{self.name}: db_table must be defined")

    def parse_table(self, response):

        header = response.css(self.header_selector).getall()
        cells = response.css(self.cell_selector).getall()

        if not header:
            raise ValueError(f"{self.name}: could not extract table header")

        table = {h: [] for h in header}
        n_cols = len(header)

        for i, cell in enumerate(cells):
            col = i % n_cols
            table[header[col]].append(cell)

        return table

    def save(self, data):

        try:
            response = self.supabase.table(self.db_table).upsert(data).execute()
            self.logger.info(f"Upsert successful: {response.data}")

        except Exception as e:
            self.logger.error(f"Upsert failed: {e}")
            raise
