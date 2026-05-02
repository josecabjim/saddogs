import os

from saddogs_scrape.spiders.base.count_spider import CountSpider
from saddogs_scrape.spiders.base.regex_spider import RegexSpider


class TenerifeValleColino(RegexSpider):
    name = "tenerife_valle_colino"

    rescue_name = "Albergue Valle Colino"
    island = "Tenerife"

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30,
    }

    start_urls = ["https://www.alberguevallecolino.org/adoptar/perros"]

    text_selector = "div.col-sm-6.text-right"
    regex_pattern = r"de\s+(\d+)"


class TenerifeTierraBlanca(RegexSpider):
    name = "tenerife_tierra_blanca"

    rescue_name = "CPA Tierra Blanca"
    island = "Tenerife"

    start_urls = ["https://cpatierrablanca.es/es/adopcion/perros-en-adopcion.html"]

    text_selector = "span.fc_item_total_data"
    regex_pattern = r"de\s+(\d+)"


class TenerifeRefugioInternacional(CountSpider):
    name = "tenerife_refugio_internacional"

    rescue_name = "Refugio Internacional para Animales"
    island = "Tenerife"

    start_urls = ["https://refugiodeanimales.org/adopta/"]

    selector = 'img[width="1080"][height="675"]'
    pagination_selector = "a.next.page-numbers::attr(href)"


class TenerifeAdejeMascotas(CountSpider):
    name = "tenerife_adeje_mascotas"

    rescue_name = "Adeje Mascotas"
    island = "Tenerife"

    start_urls = ["https://www.adeje.es/mascotas/mascotas-en-adopcion"]

    selector = "div.ListadoImgItem"

    custom_settings = {
        "HTTPPROXY_ENABLED": True,
        "HTTP_PROXY": os.environ.get("ADEJE_PROXY_URL"),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Proxy configured: {bool(os.environ.get('ADEJE_PROXY_URL'))}")
