import hashlib
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.adapters.base import FetchError
from app.adapters.discovery import DiscoverySource, QuotaExceededError
from app.core.config import settings
from app.models.discovery_source import DISCOVERY_KINDS
from app.models.discovery_source import DiscoverySource as DiscoverySourceModel
from app.models.user import User
from app.repositories.discovery_source_repository import DiscoverySourceRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead import DiscoverRunResult, DiscoverySourceRead
from app.services.url_canonicalizer import canonicalize

logger = logging.getLogger(__name__)


class DiscoverySourceNotFoundError(Exception):
    pass


class DiscoverySourceConflictError(Exception):
    pass


class DiscoveryKindError(Exception):
    """An unknown, disabled, or unconfigured discovery kind."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class DiscoveryService:
    """Manage discovery sources and turn their feeds/queries into deduped leads."""

    def __init__(
        self,
        sources: DiscoverySourceRepository,
        leads: LeadRepository,
        source_factory: Callable[[str], DiscoverySource],
    ) -> None:
        self.sources = sources
        self.leads = leads
        self._source_factory = source_factory

    def create_source(
        self, user: User, *, kind: str, label: str, target: str
    ) -> DiscoverySourceRead:
        self._check_kind(kind)
        if self.sources.get_by_target(user.id, kind, target) is not None:
            raise DiscoverySourceConflictError("Discovery source already exists")
        source = self.sources.create(user_id=user.id, kind=kind, label=label, target=target)
        self.sources.commit()
        return DiscoverySourceRead.model_validate(source)

    def list_sources(self, user: User) -> list[DiscoverySourceRead]:
        return [
            DiscoverySourceRead.model_validate(source)
            for source in self.sources.list_for_user(user.id)
        ]

    def delete_source(self, user: User, source_id: uuid.UUID) -> None:
        source = self.sources.get_for_user(user.id, source_id)
        if source is None:
            raise DiscoverySourceNotFoundError
        self.sources.delete(source)
        self.sources.commit()

    def run_source(self, user: User, source_id: uuid.UUID, *, now: datetime) -> DiscoverRunResult:
        source = self.sources.get_for_user(user.id, source_id)
        if source is None:
            raise DiscoverySourceNotFoundError
        return self._run(source, now=now)

    def run_due(self, *, now: datetime, limit: int) -> int:
        cutoff = now - timedelta(minutes=settings.lead_discovery_interval_minutes)
        ran = 0
        for source in self.sources.list_enabled(limit=limit):
            if source.last_run_at is not None and source.last_run_at > cutoff:
                continue
            try:
                self._run(source, now=now)
            except FetchError as exc:
                logger.warning("discovery source %s failed: %s", source.id, exc)
            ran += 1
        return ran

    def _run(self, source: DiscoverySourceModel, *, now: datetime) -> DiscoverRunResult:
        try:
            discovered = self._source_factory(source.kind).discover(source.target)
        except QuotaExceededError:
            self._stamp(source, now, "quota")
            raise
        except (FetchError, ValueError) as exc:
            self._stamp(source, now, "error")
            raise FetchError(source.target, f"discovery failed: {exc}") from exc

        created = 0
        existing = 0
        for lead in discovered:
            canonical_url = canonicalize(lead.url)
            dedupe_key = _dedupe_key(canonical_url)
            if self.leads.exists(source.user_id, dedupe_key):
                existing += 1
                continue
            self.leads.create(
                user_id=source.user_id,
                discovery_source_id=source.id,
                title=lead.title,
                url=lead.url,
                canonical_url=canonical_url,
                domain=lead.domain,
                status="New",
                rough_score=lead.rough_score,
                dedupe_key=dedupe_key,
            )
            created += 1
        self._stamp(source, now, "ok")
        return DiscoverRunResult(created=created, existing=existing)

    def _stamp(self, source: DiscoverySourceModel, now: datetime, status: str) -> None:
        source.last_run_at = now
        source.last_status = status
        self.sources.commit()

    @staticmethod
    def _check_kind(kind: str) -> None:
        if kind not in DISCOVERY_KINDS:
            raise DiscoveryKindError("Unknown discovery kind", status_code=400)
        if kind == "rss" and not settings.enable_rss_discovery:
            raise DiscoveryKindError("RSS discovery is disabled", status_code=403)
        if kind == "google_pse":
            if not settings.enable_google_pse:
                raise DiscoveryKindError("Google PSE discovery is disabled", status_code=403)
            if not (settings.google_pse_api_key and settings.google_pse_cx):
                raise DiscoveryKindError("Google PSE is not configured", status_code=503)


def _dedupe_key(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode()).hexdigest()


def build_discovery_service(
    db: Session, *, source_factory: Callable[[str], DiscoverySource]
) -> DiscoveryService:
    return DiscoveryService(DiscoverySourceRepository(db), LeadRepository(db), source_factory)
