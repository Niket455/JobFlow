from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response, db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    checks = {"database": "ok", "cache": "ok"}

    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        checks["database"] = "error"

    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
    except Exception:  # noqa: BLE001
        checks["cache"] = "error"

    ok = all(value == "ok" for value in checks.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ok else "degraded", "checks": checks}
