from saddogs_scrape.spiders.base.count_spider import CountSpider


class LaPalmaBenawara(CountSpider):
    name = "la_palma_benawara"

    rescue_name = "Benawara"
    island = "La Palma"

    start_urls = ["https://benafwara.es/en_GB/adopta"]

    selector = "div.s_col_no_bgcolor.pt16.pb16.col-lg-3, div.s_col_no_bgcolor.o_grid_item.g-col-lg-3.g-height-14.col-lg-3"
