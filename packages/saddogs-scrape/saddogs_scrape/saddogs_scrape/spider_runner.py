"""Spider running and monitoring utilities."""

import importlib
import logging
import os
import pkgutil

import saddogs_scrape.spiders as spiders_pkg
from scrapy import Spider, signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

KNOWN_FLAKY_SPIDERS = {"lanzarote_teguise"}


class SpiderMonitor:
    def __init__(self):
        self.results = {}

    def spider_closed(self, spider, reason):
        crawler = getattr(spider, "crawler", None)
        stats = crawler.stats.get_stats() if crawler else {}
        name = spider.name

        items = stats.get("item_scraped_count", 0)
        requests = stats.get("downloader/request_count", 0)
        responses = stats.get("downloader/response_count", 0)
        download_failures = stats.get("downloader/exception_count", 0)
        spider_exceptions = stats.get("spider_exceptions/count", 0)
        retries = stats.get("retry/count", 0)
        dupes = stats.get("dupefilter/filtered", 0)
        duration = stats.get("elapsed_time_seconds")
        http_errors = stats.get("downloader/response_status_count/500", 0) + stats.get(
            "downloader/response_status_count/404", 0
        )

        errors = []
        if reason != "finished":
            errors.append(f"CRITICAL: Spider closed with reason '{reason}'")
        if items == 0:
            errors.append("CRITICAL: No items scraped")
        if spider_exceptions > 0:
            errors.append(f"CRITICAL: {spider_exceptions} spider exceptions")
        if download_failures > 10:
            errors.append(f"CRITICAL: High download failures ({download_failures})")
        if items == 0 and responses > 0:
            errors.append(
                "CRITICAL: Site structure likely changed (responses OK, no items)"
            )
        if download_failures > 5:
            errors.append(f"HIGH: Excessive download failures ({download_failures})")
        if http_errors > 10:
            errors.append(f"HIGH: Many HTTP errors ({http_errors})")
        if responses == 0:
            errors.append("HIGH: No HTTP responses received")
        if requests > 0 and responses == 0:
            errors.append("HIGH: Requests made but no responses received")
        if retries > 5:
            errors.append(f"WARNING: High retry count ({retries})")
        if dupes > 50:
            errors.append(f"WARNING: Many duplicate requests filtered ({dupes})")
        if responses < requests * 0.5:
            errors.append(f"WARNING: Low response rate ({responses}/{requests})")
        if items > 0 and requests > 0 and (items / requests) < 0.05:
            errors.append(
                f"INFO: Low scrape efficiency ({items} items / {requests} requests)"
            )
        if duration and duration > 300:
            errors.append(f"INFO: Slow runtime ({duration:.2f}s)")

        if any(e.startswith("CRITICAL") for e in errors):
            severity = "critical"
        elif any(e.startswith("HIGH") for e in errors):
            severity = "high"
        elif any(e.startswith("WARNING") for e in errors):
            severity = "warning"
        else:
            severity = "success"

        if name in KNOWN_FLAKY_SPIDERS and severity in ("critical", "high"):
            severity = "warning"
            errors.append(
                f"WARNING: Downgraded from critical/high — {name} is a known flaky spider"
            )

        self.results[name] = {
            "name": name,
            "reason": reason,
            "items_scraped": items,
            "requests": requests,
            "responses": responses,
            "download_failures": download_failures,
            "spider_exceptions": spider_exceptions,
            "retry_count": retries,
            "dupe_filtered": dupes,
            "duration_seconds": duration,
            "http_errors": http_errors,
            "errors": errors,
            "severity": severity,
        }


def load_spiders(spider_names: list[str] | None = None):
    spiders = []
    seen_names = set()
    for _, module_name, _ in pkgutil.iter_modules(spiders_pkg.__path__):
        module = importlib.import_module(f"saddogs_scrape.spiders.{module_name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Spider)
                and attr is not Spider
                and getattr(attr, "name", None)
            ):
                if attr.name in seen_names:
                    continue
                seen_names.add(attr.name)
                if spider_names and attr.name not in spider_names:
                    continue
                spiders.append(attr)
    return spiders


def run_all_spiders(spider_names=None, verbose=False, dry_run=False):
    configure_logging({"LOG_LEVEL": "DEBUG" if verbose else "INFO"})
    logger = logging.getLogger(__name__)

    spider_classes = load_spiders(spider_names)
    logger.info(f"Spiders to run: {[s.__name__ for s in spider_classes]}")

    if not spider_classes:
        logger.warning("No spiders found.")
        return SpiderMonitor()

    monitor = SpiderMonitor()
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    proxy_url = os.environ.get("ADEJE_PROXY_URL")

    for spider_class in spider_classes:
        crawler = process.create_crawler(spider_class)
        if proxy_url and getattr(spider_class, "use_proxy", False):
            crawler.settings.set("HTTPPROXY_ENABLED", True, priority="spider")
            crawler.settings.set("HTTP_PROXY", proxy_url, priority="spider")
            logger.info(f"{spider_class.name}: proxy enabled")
        crawler.signals.connect(monitor.spider_closed, signal=signals.spider_closed)
        process.crawl(crawler, dry_run=dry_run)

    process.start()
    return monitor
    return monitor
