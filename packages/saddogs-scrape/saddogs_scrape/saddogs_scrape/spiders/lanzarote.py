import scrapy
from saddogs_scrape.spiders.base.aspnet_ajax_spider import AspNetAjaxCountSpider
from saddogs_scrape.spiders.base.playwright_spider import PlaywrightCountSpider
from saddogs_scrape.spiders.base.regex_spider import RegexSpider


class LanzaroteSaraSpider(RegexSpider):
    name = "lanzarote_sara"

    rescue_name = "Sara"
    island = "Lanzarote"

    start_urls = ["https://animales.saraprotectora.org/animales/categoria/1"]

    text_selector = "small"
    regex_pattern = r"(\d+)\s*animales"


class LanzaroteTeguise(AspNetAjaxCountSpider):
    name = "lanzarote_teguise"

    rescue_name = "Teguise"
    island = "Lanzarote"

    start_urls = ["https://albergueanimalesteguise.com/Nuestros-Animales"]


class LanzaroteCasaEstrellas(PlaywrightCountSpider):
    name = "lanzarote_casa_estrellas"

    rescue_name = "Casa de las Estrellas"
    island = "Lanzarote"

    start_urls = ["https://www.casa-de-las-estrellas.org/es/dogs"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"],
        },
    }

    selector = "div.item-link-wrapper"

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 60000,
                    },
                },
                callback=self.parse,
            )
