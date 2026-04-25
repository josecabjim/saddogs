"""Run all available spiders in the Saddogs project."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from saddogs_scrape.spider_runner import run_all_spiders

_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_FILE = Path(__file__).parent / "reports" / f"report_{_timestamp}.json"


def write_report(monitor):
    results = monitor.results
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "success": sum(1 for r in results.values() if r["severity"] == "success"),
            "warning": sum(1 for r in results.values() if r["severity"] == "warning"),
            "high": sum(1 for r in results.values() if r["severity"] == "high"),
            "critical": sum(1 for r in results.values() if r["severity"] == "critical"),
        },
        "spiders": results,
    }
    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Saddogs spiders.")
    parser.add_argument("--spider", help="Filter spiders by name (substring match)")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        monitor = run_all_spiders(
            spider_filter=args.spider,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
        write_report(monitor)

        logger = logging.getLogger(__name__)
        results = monitor.results

        critical = [r for r in results.values() if r["severity"] == "critical"]
        high = [r for r in results.values() if r["severity"] == "high"]
        warning = [r for r in results.values() if r["severity"] == "warning"]
        success = [r for r in results.values() if r["severity"] == "success"]

        logger.info("----------- SCRAPE SUMMARY -----------")
        logger.info(
            f"Total: {len(results)} | Critical: {len(critical)} | High: {len(high)} | Warning: {len(warning)} | Success: {len(success)}"
        )

        if critical or high:
            logger.error("Issues detected, sending alert email...")
            sys.exit(1)
        else:
            logger.info("All spiders healthy.")

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        with open(REPORT_FILE, "w") as f:
            json.dump({"success": [], "failed": [["pipeline", str(e)]]}, f)
        sys.exit(1)
