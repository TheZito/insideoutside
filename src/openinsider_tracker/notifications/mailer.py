import smtplib
from collections.abc import Callable
from email.message import EmailMessage

from openinsider_tracker.config import Config


class EmailSendError(Exception):
    """Raised when an email could not be sent. Callers MUST catch this per-message
    (FR-013: a failed notification must not affect the signal's visibility) rather
    than letting it abort a whole notify run."""


def send_email(
    config: Config,
    *,
    to: str,
    subject: str,
    body: str,
    smtp_client_factory: Callable[[], smtplib.SMTP] | None = None,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.notify_email_from
    message["To"] = to
    message.set_content(body)

    factory = smtp_client_factory or (
        lambda: smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10)
    )
    try:
        with factory() as smtp:
            if config.smtp_use_tls:
                smtp.starttls()
            if config.smtp_user:
                smtp.login(config.smtp_user, config.smtp_password)
            smtp.send_message(message)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, converted below
        raise EmailSendError(f"Failed to send email to {to}: {exc}") from exc
