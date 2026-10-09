import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.integrations.base import InboxProvider
from app.models.integration import Integration
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.email_message_repository import EmailMessageRepository
from app.repositories.integration_repository import IntegrationRepository
from app.repositories.job_repository import JobRepository
from app.schemas.integrations import (
    EmailClassification,
    IntegrationCreate,
    IntegrationRead,
    SyncResult,
)
from app.services.dedupe import normalized_company_name
from app.services.tailor_grounding import normalize


class IntegrationNotFoundError(Exception):
    pass


class IntegrationNotConfiguredError(Exception):
    pass


class IntegrationService:
    """Connects email providers and syncs classified messages into the status review queue."""

    def __init__(
        self,
        integrations: IntegrationRepository,
        emails: EmailMessageRepository,
        applications: ApplicationRepository,
        jobs: JobRepository,
        companies: CompanyRepository,
        provider_factory: Callable[[str], InboxProvider],
        *,
        model: str,
    ) -> None:
        self.integrations = integrations
        self.emails = emails
        self.applications = applications
        self.jobs = jobs
        self.companies = companies
        self.provider_factory = provider_factory
        self.model = model

    def connect(self, user: User, payload: IntegrationCreate) -> IntegrationRead:
        if payload.provider == "gmail" and not settings.gmail_enabled:
            raise IntegrationNotConfiguredError("Gmail integration is not configured")
        integration = self.integrations.create(
            user_id=user.id,
            provider=payload.provider,
            email_address=payload.email_address,
            status="connected",
            scopes=[],
        )
        return IntegrationRead.model_validate(integration)

    def list_for_user(self, user: User) -> list[IntegrationRead]:
        return [
            IntegrationRead.model_validate(integration)
            for integration in self.integrations.list_for_user(user.id)
        ]

    def disconnect(self, user: User, integration_id: uuid.UUID) -> None:
        self.integrations.delete(self._get(user, integration_id))

    async def sync(
        self,
        user: User,
        integration_id: uuid.UUID,
        gateway: LLMGateway,
        *,
        since: datetime | None = None,
    ) -> SyncResult:
        integration = self._get(user, integration_id)
        messages = self.provider_factory(integration.provider).fetch(since=since)
        candidates = self._company_candidates(user)
        created = 0
        skipped = 0
        for message in messages:
            if self.emails.exists(integration.id, message.external_id):
                skipped += 1
                continue
            classification = await gateway.complete_structured(
                [
                    LLMMessage(
                        role="user",
                        content=load_prompt("email_classify").format(
                            sender=message.sender,
                            subject=message.subject,
                            snippet=message.snippet,
                        ),
                    )
                ],
                model=self.model,
                schema=EmailClassification,
            )
            haystack = normalize(f"{message.sender} {message.subject} {message.snippet}")
            self.emails.create(
                user_id=user.id,
                integration_id=integration.id,
                external_id=message.external_id,
                sender=message.sender,
                subject=message.subject,
                snippet=message.snippet,
                received_at=message.received_at,
                classification=classification.classification,
                confidence=classification.confidence,
                application_id=_match_application(haystack, candidates),
                suggested_event=classification.suggested_event,
                rationale=classification.rationale,
                status="pending",
            )
            created += 1
        self.integrations.commit()
        return SyncResult(created=created, skipped=skipped)

    def _get(self, user: User, integration_id: uuid.UUID) -> Integration:
        integration = self.integrations.get_for_user(user.id, integration_id)
        if integration is None:
            raise IntegrationNotFoundError
        return integration

    def _company_candidates(self, user: User) -> list[tuple[uuid.UUID, str]]:
        applications = self.applications.list_all_for_user(user.id)
        jobs = self.jobs.get_many({application.job_id for application in applications})
        companies = self.companies.get_many(
            {job.company_id for job in jobs.values() if job.company_id is not None}
        )
        candidates: list[tuple[uuid.UUID, str]] = []
        for application in applications:
            job = jobs.get(application.job_id)
            if job is None or job.company_id is None:
                continue
            company = companies.get(job.company_id)
            if company is not None:
                candidates.append((application.id, normalized_company_name(company.name)))
        return candidates


def build_integration_service(
    db: Session, provider_factory: Callable[[str], InboxProvider]
) -> IntegrationService:
    return IntegrationService(
        IntegrationRepository(db),
        EmailMessageRepository(db),
        ApplicationRepository(db),
        JobRepository(db),
        CompanyRepository(db),
        provider_factory,
        model=settings.llm_cheap_model,
    )


def _match_application(haystack: str, candidates: list[tuple[uuid.UUID, str]]) -> uuid.UUID | None:
    best: uuid.UUID | None = None
    best_length = 0
    for application_id, company in candidates:
        if company and company in haystack and len(company) > best_length:
            best = application_id
            best_length = len(company)
    return best
