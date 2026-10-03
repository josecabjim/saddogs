import re

import scrapy
from spiders.base.base_spider import BaseRescueSpider


class PlaywrightRegexSpider(BaseRescueSpider):
    """Like RegexSpider, but renders with a real browser first. For sites whose
    bot-mitigation blocks Scrapy's plain HTTP client (soft-blocks like a 202
    holding response, or a JS challenge) regardless of source IP."""

    text_selector = None
    regex_pattern = None

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
                        "wait_until": "domcontentloaded",
                        "timeout": 60000,
                    },
                },
                callback=self.parse,
                errback=self.errback,
            )

    async def errback(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"{self.name}: request failed: {failure}")

    async def parse(self, response):
        if not self.text_selector:
            raise ValueError(f"{self.name}: text_selector must be defined")
        if not self.regex_pattern:
            raise ValueError(f"{self.name}: regex_pattern must be defined")

        page = response.meta["playwright_page"]

        try:
            await page.wait_for_selector(self.text_selector, timeout=30000)
            text = await page.inner_text(self.text_selector)
        finally:
            await page.close()

        match = re.search(self.regex_pattern, text)
        if not match:
            raise ValueError(
                f"{self.name}: Regex {self.regex_pattern} did not match text: {text!r}"
            )

        total = int(match.group(1))
        self.logger.info(f"Extracted total: {total}")

        yield self.save_result(total)
