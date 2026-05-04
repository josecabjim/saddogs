import scrapy
from spiders.base.playwright_spider import PlaywrightCountSpider


class LaGomeraProAnimal(PlaywrightCountSpider):
    name = "la_gomera_proanimal"

    rescue_name = "Pro Animal"
    island = "La Gomera"

    start_urls = ["https://www.proanimalgomera.com/refugio-virtual/perros/"]

    selector = "div.team-member"

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
