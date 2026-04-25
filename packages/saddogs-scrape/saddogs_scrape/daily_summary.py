"""Run at 22:00 UTC. Send one email if any rescues have no entry today."""

import sys

from check_missing import get_missing_spider_names
from saddogs_scrape.spiders.services.send_failure_email import send_failure_email

if __name__ == "__main__":
    missing = get_missing_spider_names()

    if not missing:
        print("All rescues have data for today. No email sent.")
        sys.exit(0)

    print(f"Missing rescues at end of day: {missing}")

    # Reuse send_failure_email with a synthetic results dict so you don't need a new email template
    results = {
        name: {
            "name": name,
            "severity": "critical",
            "errors": ["CRITICAL: No entry recorded for today"],
            "items_scraped": 0,
        }
        for name in missing
    }
    send_failure_email(results=results, subject="Daily Summary — Missing Rescue Data")
    sys.exit(1)  # marks the GH Actions job red so it's visible in the UI too
