from saddogs_scrape.spiders.base.base_spider import BaseRescueSpider


class CountSpider(BaseRescueSpider):
    selector = None
    pagination_selector = None

    def parse(self, response):

        items = response.css(self.selector)
        page_count = len(items)

        self.total_count += page_count

        next_page = None

        if self.pagination_selector:
            next_page = response.css(self.pagination_selector).get()

        if next_page:
            yield response.follow(next_page, callback=self.parse)
        else:
            yield self.save_result(self.total_count)
