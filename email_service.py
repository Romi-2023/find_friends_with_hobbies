# email_service.py – wysyłka e-maili (SMTP)
"""
Wysyłanie wiadomości e-mail (reset hasła, weryfikacja e-mail).
Konfiguracja: config.EMAIL_*
"""

import logging
import smtplib
from email.message import EmailMessage

import config

logger = logging.getLogger(__name__)


def send_email(to_addr: str, subject: str, body: str) -> bool:
    """Wysyła e-mail. Zwraca True przy sukcesie."""
    if not (config.EMAIL_HOST and config.EMAIL_USER and config.EMAIL_PASSWORD):
        logger.warning("Email not configured – cannot send mail.")
        return False

    msg = EmailMessage()
    msg["From"] = config.EMAIL_FROM
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT, timeout=10) as server:
            server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent to %s", to_addr)
        return True
    except Exception as e:
        logger.error("send_email error: %s", e)
        return False
