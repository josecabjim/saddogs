import scrapy
from saddogs_scrape.spiders.base.base_spider import BaseRescueSpider
from scrapy import Selector


class AspNetAjaxCountSpider(BaseRescueSpider):
    search_event_target = "dnn$ctr383$View$lnkSearch"
    results_selector = "span#dnn_ctr383_View_lblTotal::text"

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    }

    def parse(self, response):

        formdata = {
            "ScriptManager": f"ScriptManager|{self.search_event_target}",
            "dnn$dnnSearch2$txtSearch": "",
            "dnn$ctr383$View$chkPerro": "on",
            "dnn$ctr383$View$num_resultados": "19",
            "dnn$ctr383$View$pagina_actual": "1",
            "ScrollTop": "0",
            "__dnnVariable": response.css(
                "input[name='__dnnVariable']::attr(value)"
            ).get(),
            "__RequestVerificationToken": response.css(
                "input[name='__RequestVerificationToken']::attr(value)"
            ).get(),
            "__EVENTTARGET": self.search_event_target,
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": response.css("input[name='__VIEWSTATE']::attr(value)").get(),
            "__VIEWSTATEGENERATOR": response.css(
                "input[name='__VIEWSTATEGENERATOR']::attr(value)"
            ).get(),
            "__EVENTVALIDATION": response.css(
                "input[name='__EVENTVALIDATION']::attr(value)"
            ).get(),
            "__VIEWSTATEENCRYPTED": "",
            "__ASYNCPOST": "true",
        }

        yield scrapy.FormRequest(
            url=response.url,
            formdata=formdata,
            callback=self.parse_results,
            headers={
                "X-MicrosoftAjax": "Delta=true",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": response.url,
            },
        )

    def parse_results(self, response):

        body = response.text

        # ASP.NET async responses are pipe-delimited
        html_fragment = None
        parts = body.split("|")

        for part in parts:
            if "lblTotal" in part:
                html_fragment = part
                break

        if not html_fragment:
            raise ValueError(f"{self.name}: Could not locate ASP.NET fragment")

        sel = Selector(text=html_fragment)

        total_text = sel.css(self.results_selector).get()

        if not total_text:
            raise ValueError(f"{self.name}: Could not extract total count")

        total = int(total_text)

        yield self.save_result(total)
