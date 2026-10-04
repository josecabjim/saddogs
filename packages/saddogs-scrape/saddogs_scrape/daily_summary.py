"""Run at 22:00 UTC. Send one email with two sections: needs review (last
24h) and stale 7+ days. A one-day "missing" miss is deliberately not
reported — it's usually a transient blip that self-heals on the next 4h
scrape cycle (see OPERATIONS.md); only a rescue stale for 7+ days is
treated as actionable here."""

import sys

from check_missing import get_recent_needs_review, get_stale_spider_names
from spiders.services.send_failure_email import send_daily_report

if __name__ == "__main__":
    stale = get_stale_spider_names()
    needs_review_rescues, needs_review_census = get_recent_needs_review()

    if not any([stale, needs_review_rescues, needs_review_census]):
        print("Nothing stale or flagged for review. No email sent.")
        sys.exit(0)

    print(f"Stale 7+ days: {stale}")
    print(
        f"Needs review (last 24h): {len(needs_review_rescues)} rescue row(s), "
        f"{len(needs_review_census)} census row(s)"
    )

    send_daily_report(
        stale=stale,
        needs_review_rescues=needs_review_rescues,
        needs_review_census=needs_review_census,
        subject="Saddogs Daily Summary",
    )
    sys.exit(1)  # marks the GH Actions job red so it's visible in the UI too
