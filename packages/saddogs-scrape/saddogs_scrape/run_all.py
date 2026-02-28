"""Run all available spiders in the Saddogs project."""

import argparse
import importlib
import logging
import pkgutil
import sys
import time
from scrapy import Spider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

import saddogs_scrape.spiders as spiders_pkg


def load_spiders(spider_filter=None):
    """Dynamically load all spiders from the spiders package.

    Args:
        spider_filter: Optional string to filter spiders by name.

    Returns:
        List of spider classes.
    """
    spiders_list = []

    for loader, module_name, is_pkg in pkgutil.iter_modules(spiders_pkg.__path__):
        try:
            module = importlib.import_module(f"saddogs_scrape.spiders.{module_name}")

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Spider)
                    and attr != Spider
                ):
                    if (
                        spider_filter is None
                        or spider_filter.lower() in attr.name.lower()
                    ):
                        spiders_list.append(attr)

        except Exception as e:
            logging.error(f"Failed to import module {module_name}: {e}")

    return spiders_list


def run_all_spiders(spider_filter=None, verbose=False):
    """Run all spiders.

    Args:
        spider_filter: Optional string to filter spiders by name.
        verbose: Enable verbose logging.
    """
    # Configure logging
    configure_logging({"LOG_LEVEL": "DEBUG" if verbose else "INFO"})
    logger = logging.getLogger(__name__)

    # Load project settings
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    # Load available spiders
    spiders_list = load_spiders(spider_filter)

    if not spiders_list:
        logger.warning("No spiders found to run.")
        return

    logger.info(f"Found {len(spiders_list)} spider(s) to run.")

    # Schedule all spiders
    for spider_class in spiders_list:
        logger.info(f"Scheduling spider: {spider_class.name}")
        process.crawl(spider_class)

    # Start all spiders
    logger.info("Starting crawler process...")
    start_time = time.time()
    process.start()
    duration = time.time() - start_time

    logger.info(f"Crawler process completed in {duration:.2f}s.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Saddogs spiders.")
    parser.add_argument(
        "--spider",
        help="Filter spiders by name (case-insensitive substring match).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    try:
        run_all_spiders(spider_filter=args.spider, verbose=args.verbose)
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
