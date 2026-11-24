"""Send the report by email when SMTP is configured."""
import smtplib
from email.message import EmailMessage

from . import config
from .logging_setup import get_logger

log = get_logger("pipeline.notify")


def email_enabled() -> bool:
    return bool(config.SMTP_HOST and config.REPORT_TO)


def send_report(subject: str, html: str, text: str) -> bool:
    if not email_enabled():
        log.info("SMTP not configured; report stored in the database only.")
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, config.REPORT_FROM, ", ".join(config.REPORT_TO)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
        server.starttls()
        if config.SMTP_USER:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
    log.info("Report emailed to %s", ", ".join(config.REPORT_TO))
    return True
