"""Send email notifications for spider failures."""

import json
import logging
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from typing import Dict

logger = logging.getLogger(__name__)
REPORT_FILE = "scrape_report.json"


def send_failure_email(failed_spiders: Dict[str, str], subject: str = None) -> bool:
    """
    Send an email notification for spider failures.

    Args:
        failed_spiders: Dict mapping spider name to error(s)
        subject: Custom email subject (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    if not failed_spiders:
        logger.info("No failures to report")
        return True

    try:
        email_from = os.environ.get("EMAIL_FROM")
        email_to = os.environ.get("EMAIL_TO")
        email_password = os.environ.get("EMAIL_PASSWORD")

        if not all([email_from, email_to, email_password]):
            logger.warning(
                "Email env vars not configured (EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD). Skipping email."
            )
            return False

        body = "🚨 Saddogs Spider Health Report\n\n"
        for spider, data in failed_spiders.items():
            body += f"--- {spider} ---\n"
            body += f"Reason: {data.get('reason')}\n"
            body += f"Items scraped: {data.get('items_scraped')}\n"
            body += f"Requests: {data.get('requests')}\n"
            body += f"Download failures: {data.get('download_failures')}\n"
            body += f"Spider exceptions: {data.get('spider_exceptions')}\n"

            if data.get("exception_types"):
                body += f"Exception types: {data['exception_types']}\n"

            if data.get("errors"):
                body += "Errors:\n"
                for err in data["errors"]:
                    body += f"  - {err}\n"

            body += "\n"

        msg = MIMEText(body)
        msg["Subject"] = subject or f"Saddogs Scraper Failure ({date.today()})"
        msg["From"] = email_from
        msg["To"] = email_to

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_from, email_password)
            server.send_message(msg)

        logger.info("Failure email sent successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


if __name__ == "__main__":
    # Script mode: read from report file and send email
    logging.basicConfig(level=logging.INFO)

    try:
        with open(REPORT_FILE) as f:
            report = json.load(f)

        failed = report.get("failed", {})
        send_failure_email(failed)

    except FileNotFoundError:
        logger.error(f"Report file not found: {REPORT_FILE}")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in report file: {REPORT_FILE}")
