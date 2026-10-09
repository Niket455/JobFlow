import uuid
from typing import Any

from sqlalchemy import select

from app.models.discovery_source import DiscoverySource
from app.repositories.base import BaseRepository


class DiscoverySourceRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, source_id: uuid.UUID) -> DiscoverySource | None:
        return self.db.scalar(
            select(DiscoverySource).where(
                DiscoverySource.user_id == user_id, DiscoverySource.id == source_id
            )
        )

    def get_by_target(self, user_id: uuid.UUID, kind: str, target: str) -> DiscoverySource | None:
        return self.db.scalar(
            select(DiscoverySource).where(
                DiscoverySource.user_id == user_id,
                DiscoverySource.kind == kind,
                DiscoverySource.target == target,
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[DiscoverySource]:
        return list(
            self.db.scalars(
                select(DiscoverySource)
                .where(DiscoverySource.user_id == user_id)
                .order_by(DiscoverySource.created_at)
            )
        )

    def list_enabled(self, *, limit: int) -> list[DiscoverySource]:
        return list(
            self.db.scalars(
                select(DiscoverySource)
                .where(DiscoverySource.enabled.is_(True))
                .order_by(DiscoverySource.last_run_at.asc().nullsfirst())
                .limit(limit)
            )
        )

    def create(self, **fields: Any) -> DiscoverySource:
        source = DiscoverySource(**fields)
        self.db.add(source)
        self.db.flush()
        return source

    def delete(self, source: DiscoverySource) -> None:
        self.db.delete(source)
        self.db.flush()
