from spiders.base.count_spider import CountSpider


class FuerteventuraCentroSur(CountSpider):
    name = "fuerteventura_centro_sur"

    rescue_name = "Mancomunidad Centro Sur Fuerteventura"
    island = "Fuerteventura"

    start_urls = ["https://mancomunidadcentrosurftv.org/adopciones/"]  # noqa: RUF012 - Scrapy spider class attribute, read by the framework, never mutated per-instance

    selector = "div.ficha-animal"


# Disabled 2026-10-03: fuerteventuradogrescue.org has been squatted by an
# unrelated gambling site (domain lost, not a markup change) and redirects to
# rubyselixirdtsp.com. No replacement URL found yet; re-enable if one turns up.
# class FuerteventuraDogRescue(CountSpider):
#     name = "fuerteventura_dog_rescue"
#
#     rescue_name = "Fuerteventura Dog Rescue"
#     island = "Fuerteventura"
#
#     custom_settings = {
#         "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
#         "CONCURRENT_REQUESTS": 4,
#         "DOWNLOAD_DELAY": 1,
#         "RETRY_ENABLED": True,
#         "RETRY_TIMES": 5,
#         "DOWNLOAD_TIMEOUT": 30,
#     }
#
#     start_urls = ["https://www.fuerteventuradogrescue.org/es/perros/"]
#
#     selector = "div.wp-block-column.is-layout-flow.wp-block-column-is-layout-flow:has(h6.wp-block-heading)"
