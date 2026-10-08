from typing import Any

from app.models.fetch_log import FetchLog
from app.repositories.base import BaseRepository


class FetchLogRepository(BaseRepository):
    def create(self, **fields: Any) -> FetchLog:
        log = FetchLog(**fields)
        self.db.add(log)
        self.db.flush()
        return log
