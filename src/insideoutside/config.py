import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    db_path: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool
    notify_email_to: str
    notify_email_from: str
    poll_interval_minutes: int
    host: str
    port: int


def load_config() -> Config:
    return Config(
        db_path=os.environ.get("DB_PATH", "./data/insideoutside.db"),
        smtp_host=os.environ.get("SMTP_HOST", "localhost"),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ.get("SMTP_USER", ""),
        smtp_password=os.environ.get("SMTP_PASSWORD", ""),
        smtp_use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"),
        notify_email_to=os.environ.get("NOTIFY_EMAIL_TO", ""),
        notify_email_from=os.environ.get("NOTIFY_EMAIL_FROM", "insideoutside@localhost"),
        poll_interval_minutes=int(os.environ.get("POLL_INTERVAL_MINUTES", "60")),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
