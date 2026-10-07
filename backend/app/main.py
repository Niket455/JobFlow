from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401  (register models on Base metadata)
from app.api.system import router as system_router
from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware

configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(api_router, prefix="/api/v1")
