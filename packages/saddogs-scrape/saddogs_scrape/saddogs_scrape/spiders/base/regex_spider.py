import re

from saddogs_scrape.spiders.base.base_spider import BaseRescueSpider


class RegexSpider(BaseRescueSpider):
    # CSS selector where the text exists
    text_selector = None

    # regex used to extract the number
    regex_pattern = None

    def parse(self, response):

        if not self.text_selector:
            raise ValueError(f"{self.name}: text_selector must be defined")

        if not self.regex_pattern:
            raise ValueError(f"{self.name}: regex_pattern must be defined")

        text = response.css(self.text_selector).get()

        if not text:
            raise ValueError(
                f"{self.name}: Could not extract text using selector {self.text_selector}"
            )

        match = re.search(self.regex_pattern, text)

        if not match:
            raise ValueError(
                f"{self.name}: Regex {self.regex_pattern} did not match text: {text}"
            )

        total = int(match.group(1))

        self.logger.info(f"Extracted total: {total}")

        yield self.save_result(total)
