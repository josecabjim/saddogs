"""Run at 22:00 UTC. Send one email with three sections: missing today,
needs review (last 24h), and stale 7+ days."""

import sys

from check_missing import (
    get_missing_spider_names,
    get_recent_needs_review,
    get_stale_spider_names,
)
from spiders.services.send_failure_email import send_daily_report

if __name__ == "__main__":
    missing = get_missing_spider_names()
    stale = get_stale_spider_names()
    needs_review_rescues, needs_review_census = get_recent_needs_review()

    if not any([missing, stale, needs_review_rescues, needs_review_census]):
        print("All rescues have data for today. No email sent.")
        sys.exit(0)

    print(f"Missing today: {missing}")
    print(f"Stale 7+ days: {stale}")
    print(
        f"Needs review (last 24h): {len(needs_review_rescues)} rescue row(s), "
        f"{len(needs_review_census)} census row(s)"
    )

    send_daily_report(
        missing=missing,
        stale=stale,
        needs_review_rescues=needs_review_rescues,
        needs_review_census=needs_review_census,
        subject="Saddogs Daily Summary",
    )
    sys.exit(1)  # marks the GH Actions job red so it's visible in the UI too
