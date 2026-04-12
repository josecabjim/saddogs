"""Run all available spiders in the Saddogs project."""

import os
from xml.parsers.expat import errors

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
            "name": spider_name,
            "reason": reason,
            "items_scraped": stats.get("item_scraped_count", 0),
            "requests": stats.get("downloader/request_count", 0),
            "responses": stats.get("downloader/response_count", 0),
            "download_failures": stats.get("downloader/exception_count", 0),
            "spider_exceptions": stats.get("spider_exceptions/count", 0),
            "retry_count": stats.get("retry/count", 0),
            "dupe_filtered": stats.get("dupefilter/filtered", 0),
            "duration_seconds": stats.get("elapsed_time_seconds"),
        }

        # HTTP error aggregation
        summary["http_errors"] = stats.get(
            "downloader/response_status_count/500", 0
        ) + stats.get("downloader/response_status_count/404", 0)

        if stats.get("spider_exceptions"):
            summary["exception_types"] = stats["spider_exceptions"]

        errors = []

        # --- CRITICAL ---
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

        if summary["items_scraped"] == 0 and summary["responses"] > 0:
            errors.append(
                "CRITICAL: Site structure likely changed (responses OK, no items)"
            )

        # --- HIGH ---
        if summary["download_failures"] > 5:
            errors.append(
                f"HIGH: Excessive download failures ({summary['download_failures']})"
            )

        if summary["http_errors"] > 10:
            errors.append(f"HIGH: Many HTTP errors ({summary['http_errors']})")

        if summary["responses"] == 0:
            errors.append("HIGH: No HTTP responses received")

        if summary["requests"] > 0 and summary["responses"] == 0:
            errors.append("HIGH: Requests made but no responses received")

        # --- WARNING ---
        if summary["retry_count"] > 5:
            errors.append(f"WARNING: High retry count ({summary['retry_count']})")

        if summary["dupe_filtered"] > 50:
            errors.append(
                f"WARNING: Many duplicate requests filtered ({summary['dupe_filtered']})"
            )

        if summary["responses"] < summary["requests"] * 0.5:
            errors.append(
                f"WARNING: Low response rate ({summary['responses']}/{summary['requests']})"
            )

        # --- INFO ---
        if summary["items_scraped"] > 0 and summary["requests"] > 0:
            efficiency = summary["items_scraped"] / summary["requests"]
            if efficiency < 0.05:
                errors.append(
                    f"INFO: Low scrape efficiency ({summary['items_scraped']} items / {summary['requests']} requests)"
                )

        if summary.get("duration_seconds") and summary["duration_seconds"] > 300:
            errors.append(f"INFO: Slow runtime ({summary['duration_seconds']:.2f}s)")

        summary["errors"] = errors

        # --- Severity classification ---
        if any(e.startswith("CRITICAL") for e in errors):
            summary["severity"] = "critical"
        elif any(e.startswith("HIGH") for e in errors):
            summary["severity"] = "high"
        elif any(e.startswith("WARNING") for e in errors):
            summary["severity"] = "warning"
        else:
            summary["severity"] = "success"

        # store everything (IMPORTANT: replace old success/failed logic)
        if not hasattr(self, "results"):
            self.results = {}

        self.results[spider_name] = summary


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


def run_spiders(spider_classes, verbose=False, dry_run=False):
    """Run a specific list of spider classes. Returns a SpiderMonitor."""
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    monitor = SpiderMonitor()

    for spider_class in spider_classes:
        try:
            crawler = process.create_crawler(spider_class)
            crawler.signals.connect(monitor.spider_closed, signal=signals.spider_closed)
            process.crawl(crawler, dry_run=dry_run)
        except Exception as e:
            spider_name = getattr(spider_class, "name", spider_class.__name__)
            logging.getLogger(__name__).error(f"Failed to schedule {spider_name}: {e}")
            if not hasattr(monitor, "results"):
                monitor.results = {}
            monitor.results[spider_name] = {
                "name": spider_name,
                "severity": "critical",
                "errors": [f"CRITICAL: Failed to schedule - {e}"],
                "items_scraped": 0,
            }

    process.start()
    return monitor


def run_all_spiders(
    spider_filter=None, verbose=False, dry_run=False, max_attempts=3, retry_delay=60
):
    configure_logging({"LOG_LEVEL": "DEBUG" if verbose else "INFO"})
    logger = logging.getLogger(__name__)

    all_spider_classes = load_spiders(spider_filter)
    logger.info(f"Spiders to run: {[s.__name__ for s in all_spider_classes]}")

    if not all_spider_classes:
        logger.warning("No spiders found.")
        return SpiderMonitor()

    # Map name -> class for easy lookup during retries
    spider_class_map = {
        getattr(cls, "name", cls.__name__): cls for cls in all_spider_classes
    }

    combined_results = {}
    spiders_to_run = all_spider_classes

    for attempt in range(1, max_attempts + 1):
        logger.info(f"--- Attempt {attempt}/{max_attempts} ---")

        monitor = run_spiders(spiders_to_run, verbose=verbose, dry_run=dry_run)
        results = getattr(monitor, "results", {})

        # Merge results — only overwrite if this attempt did better
        for name, result in results.items():
            prev = combined_results.get(name)
            # Keep the best result seen across attempts
            severity_rank = {"success": 0, "warning": 1, "high": 2, "critical": 3}
            if (
                prev is None
                or severity_rank[result["severity"]] < severity_rank[prev["severity"]]
            ):
                combined_results[name] = result

        # Find spiders that still need retrying
        failed_names = {
            name
            for name, r in combined_results.items()
            if r["severity"] in ("critical", "high")
        }

        if not failed_names:
            logger.info("All spiders healthy — stopping early.")
            break

        if attempt < max_attempts:
            logger.warning(
                f"{len(failed_names)} spider(s) failed: {failed_names}. "
                f"Retrying in {retry_delay}s..."
            )
            time.sleep(retry_delay)
            spiders_to_run = [
                spider_class_map[n] for n in failed_names if n in spider_class_map
            ]
        else:
            logger.error(
                f"Giving up after {max_attempts} attempts. Still failing: {failed_names}"
            )

    # Attach final merged results to a monitor object for compatibility
    final_monitor = SpiderMonitor()
    final_monitor.results = combined_results
    return final_monitor


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

    parser.add_argument(
        "--max-attempts", type=int, default=3, help="Max retry attempts per spider"
    )
    parser.add_argument(
        "--retry-delay", type=int, default=60, help="Seconds to wait between retries"
    )

    args = parser.parse_args()

    try:
        monitor = run_all_spiders(
            spider_filter=args.spider,
            verbose=args.verbose,
            dry_run=args.dry_run,
            max_attempts=args.max_attempts,
            retry_delay=args.retry_delay,
        )

        write_report(monitor)

        logger = logging.getLogger(__name__)

        results = getattr(monitor, "results", {})

        critical = [s for s in results.values() if s["severity"] == "critical"]
        high = [s for s in results.values() if s["severity"] == "high"]
        warning = [s for s in results.values() if s["severity"] == "warning"]
        success = [s for s in results.values() if s["severity"] == "success"]

        logger.info("----------- SCRAPE SUMMARY -----------")
        logger.info(f"Total spiders: {len(results)}")
        logger.info(f"Critical: {len(critical)}")
        logger.info(f"High: {len(high)}")
        logger.info(f"Warning: {len(warning)}")
        logger.info(f"Successful: {len(success)}")

        # 🚨 send email if anything non-success
        if critical or high:
            logger.error("Issues detected, sending alert email...")
            send_failure_email(
                results=results,
                subject="Spider Health Alert",
            )
            sys.exit(1)
        else:
            logger.info("All spiders healthy.")

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)

        report = {
            "success": [],
            "failed": [["pipeline", str(e)]],
        }

        with open(REPORT_FILE, "w") as f:
            json.dump(report, f)

        sys.exit(1)
