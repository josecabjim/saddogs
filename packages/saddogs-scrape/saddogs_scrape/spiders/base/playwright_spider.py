from spiders.base.base_spider import BaseRescueSpider


class PlaywrightCountSpider(BaseRescueSpider):
    selector = None
    next_button_selector = None  # NEW

    async def parse(self, response):
        page = response.meta["playwright_page"]

        total = 0
        visited_pages = 0

        while True:
            visited_pages += 1

            await page.wait_for_timeout(2000)

            # count current page items
            items = await page.query_selector_all(self.selector)
            page_count = len(items)
            total += page_count

            self.logger.info(
                f"Page {visited_pages}: found {page_count} items (running total: {total})"
            )

            # try find "Next" button
            if not self.next_button_selector:
                break

            next_button = await page.query_selector(self.next_button_selector)

            if not next_button:
                break

            # check if disabled
            disabled = await next_button.get_attribute("disabled")
            aria_disabled = await next_button.get_attribute("aria-disabled")

            if disabled is not None or aria_disabled == "true":
                break

            # click next page
            try:
                await next_button.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                self.logger.warning(f"Failed to click next page: {e}")
                break

        await page.close()

        yield self.save_result(total)
