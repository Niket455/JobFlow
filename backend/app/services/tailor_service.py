import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.media_types import DOCX_CONTENT_TYPE
from app.core.prompts import load_prompt
from app.core.storage import ObjectStorage
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.models.tailor_run import TailorRun
from app.models.user import User
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.resume_repository import ResumeVersionRepository
from app.repositories.tailor_run_repository import TailorRunRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import ProfileData
from app.schemas.resume import ResumeVersionRead
from app.schemas.tailor import (
    ProposedChange,
    TailorChange,
    TailorDecisions,
    TailorProposal,
    TailorRequest,
    TailorRunRead,
)
from app.services.encryption import ensure_data_key
from app.services.job_service import JobNotFoundError
from app.services.resume_renderer import build_lines, render_docx
from app.services.resume_service import ResumeNotFoundError, ResumeService
from app.services.tailor_grounding import (
    AppliedChange,
    apply_changes,
    get_text,
    is_grounded,
    path_exists,
)


class TailorRunNotFoundError(Exception):
    pass


class TailorDecisionError(Exception):
    pass


class TailorRunAlreadyAppliedError(Exception):
    pass


class TailorService:
    """LLM proposes rewordings; a deterministic verifier grounds every change."""

    def __init__(
        self,
        resumes: ResumeVersionRepository,
        runs: TailorRunRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        users: UserRepository,
        storage: ObjectStorage,
        gateway: LLMGateway,
        *,
        model: str,
    ) -> None:
        self.resumes = resumes
        self.runs = runs
        self.jobs = jobs
        self.sources = sources
        self.analyses = analyses
        self.users = users
        self.storage = storage
        self.gateway = gateway
        self.model = model

    async def tailor(
        self, user: User, base_resume_id: uuid.UUID, payload: TailorRequest
    ) -> TailorRunRead:
        record = self.resumes.get_for_user(user.id, base_resume_id)
        if record is None or record.parsed_enc is None:
            raise ResumeNotFoundError
        job = self.jobs.get(payload.job_id)
        if job is None or not self.sources.exists(payload.job_id, user.id):
            raise JobNotFoundError

        data_key = ensure_data_key(user, self.users)
        base_profile = ProfileData.model_validate_json(decrypt_text(data_key, record.parsed_enc))
        base_text = decrypt_text(data_key, record.text_enc) if record.text_enc else ""
        analysis = self.analyses.get_for_job(job.id)

        prompt = load_prompt("tailor_resume").format(
            resume_json=base_profile.model_dump_json(),
            resume_text=base_text or base_profile.model_dump_json(),
            job_text=_job_text(job, analysis),
        )
        proposal = await self.gateway.complete_structured(
            [LLMMessage(role="user", content=prompt)], model=self.model, schema=TailorProposal
        )

        corpus = base_text or base_profile.model_dump_json()
        base_dump = base_profile.model_dump()
        changes = [_change(base_dump, proposed, corpus) for proposed in proposal.changes]
        run = self.runs.create(
            user_id=user.id,
            base_resume_version_id=base_resume_id,
            job_id=job.id,
            status="proposed",
            model=self.model,
            changes=[change.model_dump() for change in changes],
        )
        self.runs.commit()
        return TailorRunRead.model_validate(run)

    def get_run(self, user: User, run_id: uuid.UUID) -> TailorRunRead:
        return TailorRunRead.model_validate(self._get(user, run_id))

    def list_for_user(self, user: User) -> list[TailorRunRead]:
        return [TailorRunRead.model_validate(run) for run in self.runs.list_for_user(user.id)]

    def set_decisions(
        self, user: User, run_id: uuid.UUID, payload: TailorDecisions
    ) -> TailorRunRead:
        run = self._get(user, run_id)
        changes: list[dict[str, Any]] = [dict(change) for change in run.changes]
        for update in payload.decisions:
            if update.index >= len(changes):
                raise TailorDecisionError(f"No change at index {update.index}")
            changes[update.index]["decision"] = update.decision
        run.changes = changes
        self.runs.save(run)
        return TailorRunRead.model_validate(run)

    def apply(self, user: User, run_id: uuid.UUID) -> ResumeVersionRead:
        run = self._get(user, run_id)
        if run.status == "applied":
            raise TailorRunAlreadyAppliedError

        base = self.resumes.get_for_user(user.id, run.base_resume_version_id)
        if base is None or base.parsed_enc is None:
            raise ResumeNotFoundError
        data_key = ensure_data_key(user, self.users)
        base_profile = ProfileData.model_validate_json(decrypt_text(data_key, base.parsed_enc))

        approved = [
            AppliedChange(path=change["path"], new_text=change["new_text"])
            for change in run.changes
            if change.get("decision") == "approved"
        ]
        tailored = ProfileData.model_validate(apply_changes(base_profile.model_dump(), approved))

        docx = render_docx(tailored)
        storage_key = f"users/{user.id}/resumes/{uuid.uuid4().hex}/tailored.docx"
        self.storage.put(storage_key, docx, DOCX_CONTENT_TYPE)
        job = self.jobs.get(run.job_id)
        version = self.resumes.create(
            user_id=user.id,
            label=f"Tailored — {job.title}" if job is not None else "Tailored",
            is_master=False,
            parent_version_id=base.id,
            filename="tailored.docx",
            content_type=DOCX_CONTENT_TYPE,
            storage_key=storage_key,
            size_bytes=len(docx),
            text_enc=encrypt_text(data_key, _plain_text(tailored)),
            parsed_enc=encrypt_text(data_key, tailored.model_dump_json()),
            confidence=None,
        )
        run.status = "applied"
        run.applied_resume_version_id = version.id
        self.runs.save(run)
        return ResumeService._to_read(version, data_key)

    def _get(self, user: User, run_id: uuid.UUID) -> TailorRun:
        run = self.runs.get_for_user(user.id, run_id)
        if run is None:
            raise TailorRunNotFoundError
        return run


def build_tailor_service(db: Session, storage: ObjectStorage, gateway: LLMGateway) -> TailorService:
    return TailorService(
        ResumeVersionRepository(db),
        TailorRunRepository(db),
        JobRepository(db),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        UserRepository(db),
        storage,
        gateway,
        model=settings.llm_strong_model,
    )


def _change(base_dump: dict[str, Any], proposed: ProposedChange, corpus: str) -> TailorChange:
    grounded = path_exists(base_dump, proposed.path) and is_grounded(proposed.source_span, corpus)
    return TailorChange(
        path=proposed.path,
        old_text=get_text(base_dump, proposed.path),
        new_text=proposed.new_text,
        source_span=proposed.source_span,
        grounded=grounded,
        decision="approved" if grounded else "rejected",
    )


def _job_text(job: Job, analysis: JobAnalysis | None) -> str:
    parts = [f"Title: {job.title}"]
    if job.location:
        parts.append(f"Location: {job.location}")
    if analysis is not None:
        parts.append(f"Extracted: {json.dumps(analysis.data)}")
    if job.description:
        parts.append(job.description)
    return "\n".join(parts)


def _plain_text(profile: ProfileData) -> str:
    return "\n".join(line.text for line in build_lines(profile))
