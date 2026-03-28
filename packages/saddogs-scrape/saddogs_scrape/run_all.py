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
        crawler = getattr(spider, "crawler", None)
        stats = crawler.stats.get_stats() if crawler else {}

        spider_name = spider.name

        summary = {
            "reason": reason,
            "items_scraped": stats.get("item_scraped_count", 0),
            "requests": stats.get("downloader/request_count", 0),
            "responses": stats.get("downloader/response_count", 0),
            "http_errors": stats.get("downloader/response_status_count/500", 0)
            + stats.get("downloader/response_status_count/404", 0),
            "download_failures": stats.get("downloader/exception_count", 0),
            "spider_exceptions": stats.get("spider_exceptions/count", 0),
            "retry_count": stats.get("retry/count", 0),
            "dupe_filtered": stats.get("dupefilter/filtered", 0),
        }

        # include detailed exception types if present
        if stats.get("spider_exceptions"):
            summary["exception_types"] = stats["spider_exceptions"]

        # optional: capture a few log lines if you want later

        # define health rules
        errors = []

        # --- CRITICAL ISSUES (almost always broken spiders) ---

        if reason != "finished":
            errors.append(f"CRITICAL: Spider closed with reason '{reason}'")

        if summary["items_scraped"] == 0:
            errors.append("CRITICAL: No items scraped")

        if summary["spider_exceptions"] > 0:
            errors.append(f"CRITICAL: {summary['spider_exceptions']} spider exceptions")

        if summary["download_failures"] > 10:
            errors.append(
                f"CRITICAL: High download failures ({summary['download_failures']})"
            )

        # --- HIGH SEVERITY (likely broken or degraded) ---

        if summary["download_failures"] > 0:
            errors.append(
                f"HIGH: Excessive download failures ({summary['download_failures']})"
            )

        if summary["http_errors"] > 10:
            errors.append(f"HIGH: Many HTTP errors ({summary['http_errors']})")

        if summary["responses"] == 0:
            errors.append("HIGH: No HTTP responses received")

        if summary["requests"] > 0 and summary["responses"] == 0:
            errors.append("HIGH: Requests made but no responses received")

        # --- WARNING (suspicious / degraded behavior) ---

        if summary["items_scraped"] < 3:
            errors.append(f"WARNING: Very low item count ({summary['items_scraped']})")

        if summary["retry_count"] > 5:
            errors.append(f"WARNING: High retry count ({summary['retry_count']})")

        if summary["dupe_filtered"] > 50:
            errors.append(
                f"WARNING: Many duplicate requests filtered ({summary['dupe_filtered']})"
            )

        if summary["requests"] < 5:
            errors.append(f"WARNING: Very few requests made ({summary['requests']})")

        if summary["responses"] < summary["requests"] * 0.5:
            errors.append(
                f"WARNING: Low response rate ({summary['responses']}/{summary['requests']})"
            )

        # --- INFO / DEBUG SIGNALS (useful context, not failures) ---

        if summary["items_scraped"] > 0 and summary["requests"] > 0:
            efficiency = summary["items_scraped"] / summary["requests"]
            if efficiency < 0.05:
                errors.append(
                    f"INFO: Low scrape efficiency ({summary['items_scraped']} items / {summary['requests']} requests)"
                )

        if summary.get("duration_seconds"):
            if summary["duration_seconds"] > 300:
                errors.append(
                    f"INFO: Slow spider runtime ({summary['duration_seconds']:.2f}s)"
                )

        if errors:
            summary["errors"] = errors
            self.failed_spiders[spider_name] = summary
        else:
            self.successful_spiders.append(summary)


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
        try:
            spider_name = getattr(spider_class, "name", spider_class.__name__)
            logger.info(f"Scheduling spider: {spider_name}")
            crawler = process.create_crawler(spider_class)
            crawler.signals.connect(monitor.spider_closed, signal=signals.spider_closed)
            process.crawl(crawler, dry_run=dry_run)
        except Exception as e:
            logger.error(f"Failed to schedule spider {spider_class.name}: {e}")
            monitor.failed_spiders[spider_class.name] = str(e)

    logger.info("Starting crawler process...")

    start_time = time.time()
    process.start()
    duration = time.time() - start_time

    logger.info(f"Crawler process completed in {duration:.2f}s.")

    return monitor


def write_report(monitor):
    all_spiders = {}

    for s in monitor.successful_spiders:
        all_spiders[s["name"] if "name" in s else "unknown"] = {
            "status": "success",
            **s,
        }

    for name, data in monitor.failed_spiders.items():
        all_spiders[name] = {
            "status": "failed",
            **data,
        }

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(all_spiders),
            "success": len(monitor.successful_spiders),
            "failed": len(monitor.failed_spiders),
        },
        "spiders": all_spiders,
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
