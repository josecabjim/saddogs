import re

import scrapy
from scrapy import Selector
from spiders.base.base_spider import BaseRescueSpider


class AspNetAjaxCountSpider(BaseRescueSpider):
    """DNN/ASP.NET WebForms module. The `ctrNNN` control-id segment is assigned
    per-install by DNN and drifts whenever the site republishes the module, so
    it's read from the page itself rather than hardcoded."""

    custom_settings = {"ROBOTSTXT_OBEY": False}  # noqa: RUF012 - Scrapy spider class attribute, read by the framework, never mutated per-instance

    def parse(self, response):

        match = re.search(r"dnn_(ctr\d+)_View_lnkSearch", response.text)
        if not match:
            raise ValueError(f"{self.name}: Could not locate DNN control id")
        ctr = match.group(1)
        search_event_target = f"dnn${ctr}$View$lnkSearch"

        formdata = {
            "ScriptManager": f"ScriptManager|{search_event_target}",
            "dnn$dnnSearch2$txtSearch": "",
            f"dnn${ctr}$View$chkPerro": "on",
            f"dnn${ctr}$View$num_resultados": "19",
            f"dnn${ctr}$View$pagina_actual": "1",
            "ScrollTop": "0",
            "__dnnVariable": response.css(
                "input[name='__dnnVariable']::attr(value)"
            ).get(),
            "__RequestVerificationToken": response.css(
                "input[name='__RequestVerificationToken']::attr(value)"
            ).get(),
            "__EVENTTARGET": search_event_target,
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
            meta={"ctr": ctr},
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

        ctr = response.meta["ctr"]
        results_selector = f"span#dnn_{ctr}_View_lblTotal::text"
        total_text = sel.css(results_selector).get()

        if not total_text:
            raise ValueError(f"{self.name}: Could not extract total count")

        total = int(total_text)

        yield self.save_result(total)
