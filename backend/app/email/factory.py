from app.core.config import Settings, settings
from app.email.base import EmailSender
from app.email.console import ConsoleEmailSender
from app.email.recording import RecordingEmailSender
from app.email.smtp import SmtpEmailSender


def build_email_sender(config: Settings = settings) -> EmailSender:
    if config.email_provider == "console":
        return ConsoleEmailSender()
    if config.email_provider == "recording":
        return RecordingEmailSender()
    if config.email_provider == "smtp":
        return SmtpEmailSender(
            host=config.smtp_host,
            port=config.smtp_port,
            from_address=config.email_from,
            username=config.smtp_username,
            password=config.smtp_password,
            use_tls=config.smtp_use_tls,
            timeout=config.smtp_timeout_seconds,
        )
    raise ValueError(f"Unknown email provider: {config.email_provider}")
