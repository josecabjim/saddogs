import scrapy
from spiders.base.count_spider import CountSpider
from spiders.base.playwright_spider import PlaywrightCountSpider
from spiders.base.regex_spider import RegexSpider


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


# TODO remove if adeje with playwright works
# class TenerifeAdejeMascotas(CountSpider):
#     name = "tenerife_adeje_mascotas"
#     rescue_name = "Adeje Mascotas"
#     island = "Tenerife"
#     start_urls = ["https://www.adeje.es/mascotas/mascotas-en-adopcion"]
#     selector = "div.ListadoImgItem"
#     use_proxy = True


class TenerifeAdejeMascotas(PlaywrightCountSpider):
    name = "tenerife_adeje_mascotas"
    rescue_name = "Adeje Mascotas"
    island = "Tenerife"
    start_urls = ["https://www.adeje.es/mascotas/mascotas-en-adopcion"]
    selector = "div.ListadoImgItem"
    next_button_selector = None
    use_proxy = True

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
                        "wait_until": "commit",  # Don't wait for networkidle initially
                        "timeout": 90000,  # Increase timeout to 90 seconds
                    },
                },
                callback=self.parse,
                errback=self.errback,
            )

    async def errback(self, failure):
        self.logger.error(f"Request failed: {failure}")

    async def parse(self, response):
        page = response.meta["playwright_page"]

        # Wait for Cloudflare challenge to complete
        # Wait for either the content OR a longer timeout
        try:
            await page.wait_for_selector(self.selector, timeout=60000)
            self.logger.info("Content loaded after Cloudflare challenge")
        except Exception as e:
            self.logger.error(f"Timeout waiting for content: {e}")
            # Take a screenshot for debugging
            await page.screenshot(path="/tmp/cloudflare_failed.png")
            await page.close()
            return

        # Continue with normal parsing
        total = 0
        visited_pages = 0

        while True:
            visited_pages += 1
            await page.wait_for_timeout(2000)

            items = await page.query_selector_all(self.selector)
            page_count = len(items)
            total += page_count
            self.logger.info(
                f"Page {visited_pages}: found {page_count} items (running total: {total})"
            )

            if not self.next_button_selector:
                break

            next_button = await page.query_selector(self.next_button_selector)
            if not next_button:
                break

            disabled = await next_button.get_attribute("disabled")
            aria_disabled = await next_button.get_attribute("aria-disabled")
            if disabled is not None or aria_disabled == "true":
                break

            try:
                await next_button.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                self.logger.warning(f"Failed to click next page: {e}")
                break

        await page.close()
        yield self.save_result(total)


class TenerifeAdepac(PlaywrightCountSpider):
    name = "tenerife_adepac"

    rescue_name = "ADEPAC Canarias"
    island = "Tenerife"

    start_urls = ["https://www.adepaccanarias.com/adopta/"]

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

    # ONLY real dogs (not adopted wrapper divs)
    selector = "a.block"

    # Next page button
    next_button_selector = "button:has-text('Siguiente')"

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


class TenerifeK9(CountSpider):
    name = "tenerife_k9"

    rescue_name = "K9"
    island = "Tenerife"

    start_urls = [
        "https://www.k9tenerife.eu/category/our-animals/k9-dogs/k9-dogs-waiting-for-homes/"
    ]

    selector = "article.latestPost.excerpt"

    pagination_selector = "a.next.page-numbers::attr(href)"
