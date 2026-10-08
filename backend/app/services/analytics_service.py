from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_event import ApplicationEvent
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.analytics import (
    FunnelRead,
    RateMetric,
    RatesRead,
    RejectionBucket,
    RejectionsRead,
    StageCount,
)
from app.services import application_analytics as agg
from app.services.application_status import StatusEvent, derive

FUNNEL_ORDER = ("saved", "applied", "interview", "offer", "rejected", "withdrawn")
REJECTION_DIMENSIONS = ("source", "company", "role", "location", "resume_version", "month")


class AnalyticsService:
    """Deterministic funnel/rate/rejection analytics folded from the application event log."""

    def __init__(
        self,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        jobs: JobRepository,
        companies: CompanyRepository,
    ) -> None:
        self.applications = applications
        self.events = events
        self.jobs = jobs
        self.companies = companies

    def funnel(self, user: User) -> FunnelRead:
        rows = self._rows(user)
        counts = agg.funnel(rows)
        stages = [StageCount(stage=key, count=counts[key]) for key in FUNNEL_ORDER]
        return FunnelRead(stages=stages, total=len(rows))

    def rates(self, user: User) -> RatesRead:
        metrics = agg.rates(self._rows(user), settings.analytics_min_sample)
        return RatesRead(
            response=_metric(metrics["response"]),
            interview=_metric(metrics["interview"]),
            offer=_metric(metrics["offer"]),
            offer_from_interview=_metric(metrics["offer_from_interview"]),
        )

    def rejections(self, user: User, by: str) -> RejectionsRead:
        report = agg.rejections(self._rows(user), by, settings.analytics_min_sample)
        return RejectionsRead(
            total_rejected=report.total_rejected,
            by=by,
            buckets=[
                RejectionBucket(
                    key=bucket.key,
                    total=bucket.total,
                    rejected=bucket.rejected,
                    rate=bucket.rate,
                    sufficient_sample=bucket.sufficient_sample,
                )
                for bucket in report.buckets
            ],
            stages=report.stages,
            reasons=report.reasons,
        )

    def _rows(self, user: User) -> list[agg.ApplicationRow]:
        applications = self.applications.list_all_for_user(user.id)
        if not applications:
            return []
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        jobs = self.jobs.get_many({application.job_id for application in applications})
        companies = self.companies.get_many(
            {job.company_id for job in jobs.values() if job.company_id is not None}
        )
        rows: list[agg.ApplicationRow] = []
        for application in applications:
            events = grouped.get(application.id, [])
            job = jobs.get(application.job_id)
            company = (
                companies.get(job.company_id)
                if job is not None and job.company_id is not None
                else None
            )
            rows.append(
                agg.ApplicationRow(
                    status=_status(events),
                    event_types=[event.type for event in events],
                    source=application.source,
                    company=company.name if company is not None else None,
                    role=job.title if job is not None else None,
                    location=job.location if job is not None else None,
                    resume_version_id=(
                        str(application.resume_version_id)
                        if application.resume_version_id is not None
                        else None
                    ),
                    month=(
                        application.applied_at.strftime("%Y-%m")
                        if application.applied_at is not None
                        else None
                    ),
                    reasons=_reasons(events),
                )
            )
        return rows


def build_analytics_service(db: Session) -> AnalyticsService:
    return AnalyticsService(
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        JobRepository(db),
        CompanyRepository(db),
    )


def _status(events: list[ApplicationEvent]) -> str:
    status_events = [
        StatusEvent(type=event.type, occurred_at=event.occurred_at, created_at=event.created_at)
        for event in events
    ]
    return derive(status_events)[0]


def _reasons(events: list[ApplicationEvent]) -> list[str]:
    reasons: list[str] = []
    for event in events:
        if event.type.strip().lower() != "rejected":
            continue
        reason = event.payload.get("reason") if isinstance(event.payload, dict) else None
        if isinstance(reason, str) and reason:
            reasons.append(reason)
    return reasons


def _metric(data: agg.RateMetric) -> RateMetric:
    return RateMetric(
        numerator=data.numerator,
        denominator=data.denominator,
        value=data.value,
        sufficient_sample=data.sufficient_sample,
    )
