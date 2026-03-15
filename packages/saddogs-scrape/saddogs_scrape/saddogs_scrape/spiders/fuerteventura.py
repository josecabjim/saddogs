from saddogs_scrape.spiders.base.count_spider import CountSpider


class FuerteventuraCentroSur(CountSpider):
    name = "fuerteventura_centro_sur"

    rescue_name = "Mancomunidad Centro Sur Fuerteventura"
    island = "Fuerteventura"

    start_urls = ["https://mancomunidadcentrosurftv.org/adopciones/"]

    selector = "div.ficha-animal"


class FuerteventuraDogRescue(CountSpider):
    name = "fuerteventura_dog_rescue"

    rescue_name = "Fuerteventura Dog Rescue"
    island = "Fuerteventura"

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    start_urls = ["https://www.fuerteventuradogrescue.org/es/perros/"]

    selector = "div.wp-block-column.is-layout-flow.wp-block-column-is-layout-flow:has(h6.wp-block-heading)"
    selector = "div.wp-block-column.is-layout-flow.wp-block-column-is-layout-flow:has(h6.wp-block-heading)"
