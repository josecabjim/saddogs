"""Send email notifications for spider failures."""

import json
import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)
REPORT_FILE = "scrape_report.json"


def send_failure_email(results: dict, subject: str = None) -> bool:
    logger = logging.getLogger(__name__)

    try:
        email_from = os.environ.get("EMAIL_FROM")
        email_to = os.environ.get("EMAIL_TO")
        email_password = os.environ.get("EMAIL_PASSWORD")

        if not all([email_from, email_to, email_password]):
            logger.warning("Email env vars not configured. Skipping email.")
            return False

        # --- classify ---
        critical = []
        high = []
        warning = []
        success = []

        for name, data in results.items():
            sev = data.get("severity")
            if sev == "critical":
                critical.append((name, data))
            elif sev == "high":
                high.append((name, data))
            elif sev == "warning":
                warning.append((name, data))
            else:
                success.append((name, data))

        # --- build email ---
        body = "🚨 Saddogs Spider Health Report\n\n"

        # summary
        body += "Summary\n-------\n"
        body += f"❌ Critical: {len(critical)}\n"
        body += f"🔥 High: {len(high)}\n"
        body += f"⚠️ Warning: {len(warning)}\n"
        body += f"✅ Healthy: {len(success)}\n"
        body += f"Total: {len(results)}\n\n"

        # --- CRITICAL ---
        if critical:
            body += "❌ CRITICAL ISSUES\n------------------\n\n"
            for name, data in critical:
                body += f"{name}\n"
                for err in data.get("errors", []):
                    if err.startswith(("CRITICAL", "HIGH")):
                        body += f"  - ❌ {err}\n"
                body += "\n"

        # --- HIGH ---
        if high:
            body += "\n🔥 HIGH ISSUES\n--------------\n\n"
            for name, data in high:
                body += f"{name}\n"
                for err in data.get("errors", []):
                    if err.startswith("HIGH"):
                        body += f"  - 🔥 {err}\n"
                body += "\n"

        # --- collapse common warnings ---
        low_item_spiders = [
            name
            for name, data in warning
            if any("Very low item count" in e for e in data.get("errors", []))
        ]

        if low_item_spiders:
            body += "\n⚠️ WARNINGS\n-----------\n\n"
            body += (
                f"{len(low_item_spiders)} spiders returned very low item counts:\n  "
            )
            body += ", ".join(low_item_spiders[:10])
            if len(low_item_spiders) > 10:
                body += " ..."
            body += "\n\n"

        # --- send ---
        msg = MIMEText(body)
        msg["Subject"] = subject or "Saddogs Spider Health Alert"
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
