from spiders.base.base_spider import BaseRescueSpider


class ElHierroBuscamosHogarSpider(BaseRescueSpider):
    name = "e_hierro_el_juaclo"

    rescue_name = "El Juaclo"
    island = "El Hierro"

    start_urls = ["https://tierheimelhierro.de.tl/Buscamos-un-nuevo-hogar.htm"]

    def parse(self, response):

        # Step 1: get all candidate td cells inside the adoption table area
        cells = response.xpath(
            "//div[contains(@style,'min-height') or .//h3[contains(.,'Buscamos')]]//td"
        )

        valid_dogs = []

        for td in cells:
            # extract dog link
            link = td.xpath(".//a/@href").get()

            # must exist and be a real dog page
            if not link or ".htm" not in link:
                continue

            # must contain image (real listing)
            img = td.xpath(".//img")
            if not img:
                continue

            # must contain actual name text (not empty td)
            text = td.xpath("normalize-space(text())").get()
            if not text:
                continue

            # exclude pure whitespace / layout cells
            if len(text.strip()) < 2:
                continue

            valid_dogs.append(link)

        count = len(valid_dogs)

        self.logger.info(f"Valid adoptable dogs found: {count}")

        yield self.save_result(count)
