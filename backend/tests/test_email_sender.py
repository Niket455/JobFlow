import smtplib

import pytest

from app.core.config import Settings
from app.email.base import EmailError, EmailMessage
from app.email.console import ConsoleEmailSender
from app.email.factory import build_email_sender
from app.email.recording import RecordingEmailSender
from app.email.smtp import SmtpEmailSender


class _FakeSmtp:
    instances: list["_FakeSmtp"] = []

    def __init__(self, host: str, port: int, timeout: float | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.sent: list[object] = []
        _FakeSmtp.instances.append(self)

    def __enter__(self) -> "_FakeSmtp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message: object) -> None:
        self.sent.append(message)


def test_recording_sender_captures_messages() -> None:
    sender = RecordingEmailSender()
    sender.send(EmailMessage(to="a@b.com", subject="Hi", text="Body"))
    assert len(sender.outbox) == 1
    assert sender.outbox[0].to == "a@b.com"


def test_console_sender_runs_without_error() -> None:
    ConsoleEmailSender().send(EmailMessage(to="a@b.com", subject="Hi", text="Body"))


def test_factory_selects_provider() -> None:
    assert isinstance(
        build_email_sender(Settings(email_provider="recording")), RecordingEmailSender
    )
    assert isinstance(build_email_sender(Settings(email_provider="console")), ConsoleEmailSender)
    smtp = build_email_sender(Settings(email_provider="smtp", smtp_host="mail", smtp_port=2525))
    assert isinstance(smtp, SmtpEmailSender)


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        build_email_sender(Settings(email_provider="carrier-pigeon"))


def test_smtp_sender_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSmtp.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSmtp)
    sender = SmtpEmailSender(
        host="mail.example.com",
        port=2525,
        from_address="no-reply@example.com",
        username="user",
        password="secret",
        use_tls=True,
    )

    sender.send(EmailMessage(to="a@b.com", subject="Hi", text="Body"))

    client = _FakeSmtp.instances[-1]
    assert client.host == "mail.example.com"
    assert client.port == 2525
    assert client.started_tls is True
    assert client.logged_in == ("user", "secret")
    assert len(client.sent) == 1
    message = client.sent[0]
    assert message["To"] == "a@b.com"  # type: ignore[attr-defined]
    assert message["Subject"] == "Hi"  # type: ignore[attr-defined]
    assert "Body" in message.get_content()  # type: ignore[attr-defined]


def test_smtp_sender_skips_login_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSmtp.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSmtp)
    sender = SmtpEmailSender(host="mail", port=25, from_address="x@y.com", use_tls=False)

    sender.send(EmailMessage(to="a@b.com", subject="s", text="t"))

    client = _FakeSmtp.instances[-1]
    assert client.logged_in is None
    assert client.started_tls is False


def test_smtp_sender_wraps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Boom(_FakeSmtp):
        def send_message(self, message: object) -> None:
            raise smtplib.SMTPException("nope")

    monkeypatch.setattr(smtplib, "SMTP", _Boom)
    sender = SmtpEmailSender(host="mail", port=25, from_address="x@y.com")

    with pytest.raises(EmailError):
        sender.send(EmailMessage(to="a@b.com", subject="s", text="t"))
