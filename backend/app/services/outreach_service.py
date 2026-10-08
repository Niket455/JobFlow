import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.contact import Contact
from app.models.outreach_draft import OutreachDraft
from app.models.user import User
from app.repositories.contact_repository import ContactRepository
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.outreach_draft_repository import OutreachDraftRepository
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.crm import (
    OutreachClaimRead,
    OutreachDraftProposal,
    OutreachDraftRead,
    OutreachDraftSummary,
    OutreachRequest,
)
from app.schemas.profile import ProfileData
from app.services.contact_service import ContactNotFoundError
from app.services.encryption import ensure_data_key
from app.services.job_context import job_text
from app.services.job_service import JobNotFoundError
from app.services.tailor_grounding import is_grounded


class OutreachDraftNotFoundError(Exception):
    pass


class OutreachService:
    """LLM drafts a grounded outreach message; a deterministic verifier checks each claim."""

    def __init__(
        self,
        contacts: ContactRepository,
        drafts: OutreachDraftRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
        resumes: ResumeVersionRepository,
        analyses: JobAnalysisRepository,
        users: UserRepository,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.contacts = contacts
        self.drafts = drafts
        self.jobs = jobs
        self.sources = sources
        self.resumes = resumes
        self.analyses = analyses
        self.users = users
        self.gateway = gateway
        self.model = model

    async def generate(self, user: User, payload: OutreachRequest) -> OutreachDraftRead:
        contact = self.contacts.get_for_user(user.id, payload.contact_id)
        if contact is None:
            raise ContactNotFoundError

        job = None
        context = "(no specific job)"
        if payload.job_id is not None:
            job = self.jobs.get(payload.job_id)
            if job is None or not self.sources.exists(payload.job_id, user.id):
                raise JobNotFoundError
            context = job_text(job, self.analyses.get_for_job(job.id))

        data_key = ensure_data_key(user, self.users)
        resume_json, resume_text = self._resume_context(user, data_key, payload.resume_version_id)
        contact_text = _contact_text(contact)
        prompt = load_prompt("outreach").format(
            kind=payload.kind,
            contact=contact_text,
            job_text=context,
            resume_json=resume_json,
            resume_text=resume_text or resume_json,
            instructions=payload.instructions or "(none)",
        )
        proposal = await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)],
            model=self.model,
            schema=OutreachDraftProposal,
        )

        corpus = f"{resume_text}\n{context}\n{contact_text}"
        claims = [
            OutreachClaimRead(
                text=claim.text,
                source_span=claim.source_span,
                grounded=is_grounded(claim.source_span, corpus),
            )
            for claim in proposal.claims
        ]
        draft = self.drafts.create(
            user_id=user.id,
            contact_id=contact.id,
            job_id=job.id if job is not None else None,
            kind=payload.kind,
            subject=proposal.subject,
            body_enc=encrypt_text(data_key, proposal.body),
            model=self.model,
            grounding=[claim.model_dump() for claim in claims],
            status="draft",
        )
        self.drafts.commit()
        return _to_read(draft, data_key)

    def get(self, user: User, draft_id: uuid.UUID) -> OutreachDraftRead:
        return _to_read(self._get(user, draft_id), ensure_data_key(user, self.users))

    def list_for_user(self, user: User) -> list[OutreachDraftSummary]:
        return [
            OutreachDraftSummary.model_validate(draft)
            for draft in self.drafts.list_for_user(user.id)
        ]

    def mark_sent(self, user: User, draft_id: uuid.UUID) -> OutreachDraftRead:
        draft = self._get(user, draft_id)
        data_key = ensure_data_key(user, self.users)
        draft.status = "sent"
        if draft.contact_id is not None:
            contact = self.contacts.get_for_user(user.id, draft.contact_id)
            if contact is not None:
                contact.last_contacted_at = datetime.now(UTC)
                self.contacts.save(contact)
        self.drafts.save(draft)
        return _to_read(draft, data_key)

    def _get(self, user: User, draft_id: uuid.UUID) -> OutreachDraft:
        draft = self.drafts.get_for_user(user.id, draft_id)
        if draft is None:
            raise OutreachDraftNotFoundError
        return draft

    def _resume_context(
        self, user: User, data_key: str, resume_version_id: uuid.UUID | None
    ) -> tuple[str, str]:
        if resume_version_id is not None:
            record = self.resumes.get_for_user(user.id, resume_version_id)
        else:
            records = self.resumes.list_for_user(user.id)
            record = records[-1] if records else None
        if record is None or record.parsed_enc is None:
            return "{}", ""
        profile = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        text = decrypt_text(data_key, record.text_enc) if record.text_enc else ""
        return profile.model_dump_json(), text


def build_outreach_service(db: Session, gateway: LLMGateway) -> OutreachService:
    return OutreachService(
        ContactRepository(db),
        OutreachDraftRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
        ResumeVersionRepository(db),
        JobAnalysisRepository(db),
        UserRepository(db),
        gateway,
        model=settings.llm_strong_model,
    )


def _contact_text(contact: Contact) -> str:
    parts = [f"Name: {contact.name}"]
    if contact.title:
        parts.append(f"Title: {contact.title}")
    if contact.company_name:
        parts.append(f"Company: {contact.company_name}")
    parts.append(f"Relationship: {contact.relationship}")
    return "\n".join(parts)


def _to_read(draft: OutreachDraft, data_key: str) -> OutreachDraftRead:
    claims = [OutreachClaimRead(**item) for item in draft.grounding]
    return OutreachDraftRead(
        id=draft.id,
        contact_id=draft.contact_id,
        job_id=draft.job_id,
        kind=draft.kind,
        subject=draft.subject,
        body=decrypt_text(data_key, draft.body_enc),
        model=draft.model,
        claims=claims,
        blocked_count=sum(1 for claim in claims if not claim.grounded),
        status=draft.status,
        created_at=draft.created_at,
    )
