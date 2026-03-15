from saddogs_scrape.spiders.base.base_spider import BaseRescueSpider


class PlaywrightCountSpider(BaseRescueSpider):
    selector = None

    async def parse(self, response):

        page = response.meta["playwright_page"]

        await page.wait_for_timeout(5000)

        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        items = await page.query_selector_all(self.selector)

        count = len(items)

        await page.close()

        yield self.save_result(count)
