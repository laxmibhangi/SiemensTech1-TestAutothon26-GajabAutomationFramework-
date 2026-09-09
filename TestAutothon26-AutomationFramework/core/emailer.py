"""SMTP helper used by journey step 7 - email the Deal of the Day details."""
from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

from config.settings import DOWNLOAD_DIR, config
from core.logger import get_logger

log = get_logger(__name__)


def download_image(url: str, filename: str = "deal_of_the_day.png") -> Path:
    """Download a product image to the reports folder and return its path.

    Next.js serves optimised images from /_next/image?url=... which needs a
    browser-like Accept header, otherwise it can return 400.
    """
    target = DOWNLOAD_DIR / filename
    response = requests.get(
        url,
        timeout=30,
        headers={
            "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestAutothon",
        },
    )
    response.raise_for_status()
    target.write_bytes(response.content)
    log.info("Saved product image -> %s (%d bytes)", target, target.stat().st_size)
    return target


def send_email(subject: str, body: str, attachments: list[Path] | None = None,
               html: str | None = None) -> None:
    """Send an email with optional attachments.

    Credentials come from the environment only - nothing is stored in the repo.
    Port 465 uses implicit SSL, anything else uses STARTTLS.
    """
    missing = [
        name for name, value in (
            ("SMTP_HOST", config.SMTP_HOST),
            ("SMTP_USER", config.SMTP_USER),
            ("SMTP_PASSWORD", config.SMTP_PASSWORD),
            ("EMAIL_TO", config.EMAIL_TO),
        ) if not value
    ]
    if missing:
        raise RuntimeError(
            "SMTP is not configured. Add these to your .env file: "
            + ", ".join(missing)
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.SMTP_USER
    message["To"] = config.EMAIL_TO
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")

    for path in attachments or []:
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        message.add_attachment(
            path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name
        )

    if config.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(message)

    log.info("Email '%s' sent to %s", subject, config.EMAIL_TO)
