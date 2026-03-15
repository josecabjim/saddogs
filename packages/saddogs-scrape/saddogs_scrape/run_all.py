"""Run all available spiders in the Saddogs project."""

import os

# Needed for Github Actions to avoid twisted reactor errors when running multiple spiders sequentially
if os.environ.get("CI", "false").lower() == "true":
    from twisted.internet import asyncioreactor

    asyncioreactor.install()

import argparse
import importlib
import json
import logging
import pkgutil
import sys
import time
from datetime import datetime
from pathlib import Path

import saddogs_scrape.spiders as spiders_pkg
from saddogs_scrape.spiders.services.send_failure_email import send_failure_email
from scrapy import Spider, signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_FILE = Path(__file__).parent / "reports" / f"report_{_timestamp}.json"


class SpiderMonitor:
    """Monitor the status of each spider and catch exceptions."""

    def __init__(self):
        self.successful_spiders = []
        self.failed_spiders = {}  # spider_name -> list of errors

    def spider_closed(self, spider, reason):
        stats = (
            getattr(spider, "crawler", None).stats.get_stats()
            if getattr(spider, "crawler", None)
            else {}
        )

        # count download failures
        download_failures = stats.get("downloader/exception_count", 0)
        # count spider exceptions (parse errors, etc.)
        spider_exceptions = stats.get("spider_exceptions/count", 0)

        # collect exception messages if any
        exception_types = stats.get("spider_exceptions", {})

        errors = []
        if download_failures > 0:
            errors.append(f"Download failures: {download_failures}")
        if spider_exceptions > 0:
            errors.append(f"Spider exceptions: {exception_types}")

        # if anything went wrong or reason not 'finished', mark as failed
        if errors or reason != "finished":
            self.failed_spiders[spider.name] = errors or reason
        else:
            self.successful_spiders.append(spider.name)


def load_spiders(spider_filter=None):

    spiders_list = []

    for _, module_name, _ in pkgutil.iter_modules(spiders_pkg.__path__):
        module = importlib.import_module(f"saddogs_scrape.spiders.{module_name}")

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            if (
                isinstance(attr, type)
                and issubclass(attr, Spider)
                and attr != Spider
                and getattr(attr, "name", None)
            ):
                if spider_filter and spider_filter.lower() not in attr.name.lower():
                    continue

                spiders_list.append(attr)

    return spiders_list


def run_all_spiders(spider_filter=None, verbose=False, dry_run=False):
    """Run all spiders with robust monitoring and optional dry-run mode."""
    configure_logging({"LOG_LEVEL": "DEBUG" if verbose else "INFO"})
    logger = logging.getLogger(__name__)

    settings = get_project_settings()
    process = CrawlerProcess(settings)

    monitor = SpiderMonitor()
    spiders_list = load_spiders(spider_filter)
    logger.info(f"Spiders loaded: {[spider.__name__ for spider in spiders_list]}")

    if not spiders_list:
        logger.warning("No spiders found to run.")
        return monitor

    logger.info(f"Found {len(spiders_list)} spider(s) to run.")

    for spider_class in spiders_list:
        spider_name = getattr(spider_class, "name", spider_class.__name__)
        logger.info(f"Scheduling spider: {spider_name}")

        crawler = process.create_crawler(spider_class)

        # Attach monitor signal handlers
        crawler.signals.connect(monitor.spider_closed, signal=signals.spider_closed)

        process.crawl(crawler, dry_run=dry_run)

    logger.info("Starting crawler process...")

    start_time = time.time()
    process.start()
    duration = time.time() - start_time

    logger.info(f"Crawler process completed in {duration:.2f}s.")

    return monitor


def write_report(monitor):

    report = {
        "success": monitor.successful_spiders,
        "failed": monitor.failed_spiders,
    }
    REPORT_FILE.parent.mkdir(exist_ok=True)

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Saddogs spiders.")

    parser.add_argument(
        "--spider",
        help="Filter spiders by name (case-insensitive substring match)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run spiders without saving results to the database.",
    )

    args = parser.parse_args()

    try:
        monitor = run_all_spiders(
            spider_filter=args.spider,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )

        write_report(monitor)

        logger = logging.getLogger(__name__)

        logger.info("----------- SCRAPE SUMMARY -----------")
        logger.info(f"Successful spiders: {len(monitor.successful_spiders)}")
        logger.info(monitor.successful_spiders)

        if monitor.failed_spiders:
            logger.error(f"Failed spiders: {len(monitor.failed_spiders)}")
            logger.error(monitor.failed_spiders)
            send_failure_email(
                failed_spiders=monitor.failed_spiders,
                subject="Spider Health Alert",
            )
        else:
            logger.info("All spiders completed successfully.")

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)

        report = {
            "success": [],
            "failed": [["pipeline", str(e)]],
        }

        with open(REPORT_FILE, "w") as f:
            json.dump(report, f)

        sys.exit(1)
        sys.exit(1)
