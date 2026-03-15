import json
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText

REPORT_FILE = "scrape_report.json"

with open(REPORT_FILE) as f:
    report = json.load(f)

failed = report.get("failed", [])

if not failed:
    print("No failures detected")
    exit(0)

body = "Saddogs scraping completed with failures.\n\n"

for spider, reason in failed:
    body += f"{spider} -> {reason}\n"

msg = MIMEText(body)


msg["Subject"] = f"Saddogs Scraper Failure ({date.today()})"
msg["From"] = os.environ["EMAIL_FROM"]
msg["To"] = os.environ["EMAIL_TO"]

smtp_server = "smtp.gmail.com"
smtp_port = 587

with smtplib.SMTP(smtp_server, smtp_port) as server:
    server.starttls()
    server.login(os.environ["EMAIL_FROM"], os.environ["EMAIL_PASSWORD"])
    server.send_message(msg)

print("Failure email sent.")
