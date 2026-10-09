import uuid

from sqlalchemy.orm import Session

from app.models.email_message import EmailMessage
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.calendar_suggestion_repository import CalendarSuggestionRepository
from app.repositories.email_message_repository import EmailMessageRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.application import ApplicationEventCreate
from app.schemas.integrations import EmailRead, EmailSuggestion
from app.services.application_service import ApplicationService


class EmailMessageNotFoundError(Exception):
    pass


class EmailNotActionableError(Exception):
    pass


class EmailService:
    """The status review queue: suggest, accept (writes an application event), or dismiss."""

    def __init__(
        self,
        emails: EmailMessageRepository,
        calendar: CalendarSuggestionRepository,
        applications: ApplicationService,
    ) -> None:
        self.emails = emails
        self.calendar = calendar
        self.applications = applications

    def list_for_user(self, user: User, *, status: str | None = None) -> list[EmailRead]:
        return [
            EmailRead.model_validate(message)
            for message in self.emails.list_for_user(user.id, status=status)
        ]

    def get(self, user: User, message_id: uuid.UUID) -> EmailRead:
        return EmailRead.model_validate(self._get(user, message_id))

    def suggest(self, user: User, message_id: uuid.UUID) -> EmailSuggestion:
        message = self._get(user, message_id)
        return EmailSuggestion(
            application_id=message.application_id,
            event_type=message.suggested_event,
            rationale=message.rationale,
            confidence=message.confidence,
        )

    def accept(self, user: User, message_id: uuid.UUID) -> EmailRead:
        message = self._get(user, message_id)
        if message.application_id is None or message.suggested_event is None:
            raise EmailNotActionableError
        self.applications.add_event(
            user,
            message.application_id,
            ApplicationEventCreate(type=message.suggested_event),
        )
        if message.classification == "interview":
            self.calendar.create(
                user_id=user.id,
                application_id=message.application_id,
                email_message_id=message.id,
                kind="interview",
                title=f"Interview: {message.subject}",
                proposed_at=None,
                notes=None,
                status="suggested",
            )
        message.status = "accepted"
        self.emails.save(message)
        return EmailRead.model_validate(message)

    def dismiss(self, user: User, message_id: uuid.UUID) -> EmailRead:
        message = self._get(user, message_id)
        message.status = "dismissed"
        self.emails.save(message)
        return EmailRead.model_validate(message)

    def _get(self, user: User, message_id: uuid.UUID) -> EmailMessage:
        message = self.emails.get_for_user(user.id, message_id)
        if message is None:
            raise EmailMessageNotFoundError
        return message


def build_email_service(db: Session) -> EmailService:
    return EmailService(
        EmailMessageRepository(db),
        CalendarSuggestionRepository(db),
        ApplicationService(
            ApplicationRepository(db),
            ApplicationEventRepository(db),
            JobRepository(db),
            JobSourceRepository(db),
        ),
    )
