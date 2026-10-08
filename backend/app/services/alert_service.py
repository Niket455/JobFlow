import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.email.base import EmailSender
from app.models.alert import Alert
from app.models.alert_run import AlertRun
from app.repositories.alert_repository import AlertRepository
from app.repositories.alert_run_repository import AlertRunRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.user_repository import UserRepository
from app.schemas.alert import (
    AlertData,
    AlertItem,
    AlertRead,
    AlertRunRead,
    AlertSummary,
)
from app.services.alert_schedule import in_quiet_hours, next_run_at
from app.services.notification_service import EmailDisabledError, NotificationService


class AlertNotFoundError(Exception):
    pass


class AlertService:
    """Scheduled, idempotent digests of newly-matching jobs, delivered by email."""

    def __init__(
        self,
        alerts: AlertRepository,
        runs: AlertRunRepository,
        matches: MatchRepository,
        jobs: JobRepository,
        companies: CompanyRepository,
        users: UserRepository,
        notifications: NotificationService,
    ) -> None:
        self.alerts = alerts
        self.runs = runs
        self.matches = matches
        self.jobs = jobs
        self.companies = companies
        self.users = users
        self.notifications = notifications

    def create(self, user_id: uuid.UUID, payload: AlertData) -> AlertRead:
        alert = self.alerts.create(
            user_id=user_id,
            name=payload.name,
            enabled=payload.enabled,
            frequency=payload.frequency,
            min_overall=payload.min_overall,
            quiet_hours_start=payload.quiet_hours_start,
            quiet_hours_end=payload.quiet_hours_end,
            unsubscribe_token=uuid.uuid4().hex,
            next_run_at=next_run_at(datetime.now(UTC), payload.frequency),
        )
        self.alerts.commit()
        return AlertRead.model_validate(alert)

    def update(self, user_id: uuid.UUID, alert_id: uuid.UUID, payload: AlertData) -> AlertRead:
        alert = self._get(user_id, alert_id)
        alert.name = payload.name
        alert.enabled = payload.enabled
        alert.frequency = payload.frequency
        alert.min_overall = payload.min_overall
        alert.quiet_hours_start = payload.quiet_hours_start
        alert.quiet_hours_end = payload.quiet_hours_end
        self.alerts.save(alert)
        return AlertRead.model_validate(alert)

    def delete(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> None:
        self.alerts.delete(self._get(user_id, alert_id))
        self.alerts.commit()

    def get(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> AlertRead:
        return AlertRead.model_validate(self._get(user_id, alert_id))

    def list_for_user(self, user_id: uuid.UUID) -> list[AlertSummary]:
        return [AlertSummary.model_validate(alert) for alert in self.alerts.list_for_user(user_id)]

    def preview(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> list[AlertItem]:
        return self._items(self._get(user_id, alert_id))

    def run_now(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> AlertRunRead:
        alert = self._get(user_id, alert_id)
        return AlertRunRead.model_validate(self.run_alert(alert, scheduled_for=datetime.now(UTC)))

    def list_runs(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> list[AlertRunRead]:
        alert = self._get(user_id, alert_id)
        return [AlertRunRead.model_validate(run) for run in self.runs.list_for_alert(alert.id)]

    def run_due(self, *, now: datetime, limit: int) -> int:
        alerts = self.alerts.list_due(now, limit=limit)
        for alert in alerts:
            self.run_alert(alert, scheduled_for=alert.next_run_at or now)
        return len(alerts)

    def unsubscribe(self, token: str) -> bool:
        alert = self.alerts.get_by_token(token)
        if alert is None:
            return False
        alert.enabled = False
        self.alerts.save(alert)
        return True

    def run_alert(self, alert: Alert, *, scheduled_for: datetime) -> AlertRun:
        key = f"{alert.id}:{scheduled_for.isoformat()}"
        existing = self.runs.get_by_key(key)
        if existing is not None:
            return existing

        started = datetime.now(UTC)
        if in_quiet_hours(scheduled_for.hour, alert.quiet_hours_start, alert.quiet_hours_end):
            alert.next_run_at = _quiet_end(scheduled_for, alert.quiet_hours_end)
            return self._finish(alert, key, started, status="skipped", items=[])

        items = self._items(alert)
        if not items:
            self._advance(alert, scheduled_for)
            return self._finish(alert, key, started, status="skipped", items=[])

        user = self.users.get_by_id(alert.user_id)
        assert user is not None
        try:
            self.notifications.send(user, _subject(alert, len(items)), _body(items))
        except EmailDisabledError:
            alert.next_run_at = next_run_at(scheduled_for, alert.frequency)
            return self._finish(alert, key, started, status="skipped", items=items)
        except Exception as exc:  # noqa: BLE001 — never let one alert break the batch
            alert.next_run_at = next_run_at(scheduled_for, alert.frequency)
            return self._finish(alert, key, started, status="error", items=items, error=str(exc))
        self._advance(alert, scheduled_for)
        return self._finish(alert, key, started, status="ok", items=items)

    def _advance(self, alert: Alert, scheduled_for: datetime) -> None:
        alert.last_run_at = scheduled_for
        alert.next_run_at = next_run_at(scheduled_for, alert.frequency)

    def _finish(
        self,
        alert: Alert,
        key: str,
        started: datetime,
        *,
        status: str,
        items: list[AlertItem],
        error: str | None = None,
    ) -> AlertRun:
        run = self.runs.create(
            alert_id=alert.id,
            status=status,
            items_count=len(items),
            job_ids=[str(item.job_id) for item in items],
            error=error[:500] if error else None,
            idempotency_key=key,
            started_at=started,
            finished_at=datetime.now(UTC),
        )
        self.runs.commit()
        self.runs.db.refresh(run)
        return run

    def _items(self, alert: Alert) -> list[AlertItem]:
        matches = self.matches.list_eligible(
            alert.user_id, min_overall=alert.min_overall, since=alert.last_run_at
        )
        if not matches:
            return []
        jobs = self.jobs.get_many({match.job_id for match in matches})
        companies = self.companies.get_many(
            {job.company_id for job in jobs.values() if job.company_id is not None}
        )
        items: list[AlertItem] = []
        for match in matches:
            job = jobs.get(match.job_id)
            if job is None:
                continue
            company = companies.get(job.company_id) if job.company_id is not None else None
            items.append(
                AlertItem(
                    job_id=job.id,
                    title=job.title,
                    company=company.name if company is not None else None,
                    overall=match.overall,
                    recommendation=match.recommendation,
                )
            )
        return items

    def _get(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> Alert:
        alert = self.alerts.get_for_user(user_id, alert_id)
        if alert is None:
            raise AlertNotFoundError
        return alert


def build_alert_service(db: Session, sender: EmailSender) -> AlertService:
    return AlertService(
        AlertRepository(db),
        AlertRunRepository(db),
        MatchRepository(db),
        JobRepository(db),
        CompanyRepository(db),
        UserRepository(db),
        NotificationService(sender),
    )


def _quiet_end(scheduled_for: datetime, end_hour: int | None) -> datetime:
    if end_hour is None:
        return scheduled_for
    candidate = scheduled_for.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    if candidate <= scheduled_for:
        candidate += timedelta(days=1)
    return candidate


def _subject(alert: Alert, count: int) -> str:
    return f"{alert.name}: {count} new {'match' if count == 1 else 'matches'}"


def _body(items: list[AlertItem]) -> str:
    lines = ["New job matches for you:", ""]
    for item in items:
        company = f" at {item.company}" if item.company else ""
        lines.append(f"- {item.title}{company} — {item.overall:.1f}/10 ({item.recommendation})")
    return "\n".join(lines)
