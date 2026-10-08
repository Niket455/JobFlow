import json
from collections.abc import Iterator

import pytest
from fake_fetcher import BLOCKED_URL, FakeFetcher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_email_sender, get_fetcher, get_gateway, get_storage
from app.core.db import Base, get_db
from app.core.storage import InMemoryStorage
from app.email.recording import RecordingEmailSender
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app

EXTRACTION_JSON = json.dumps(
    {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "summary": "Data engineer",
        "skills": ["Python", "SQL", "PySpark"],
        "confidence": {"personal": 0.95, "skills": 0.8},
    }
)


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def fake_fetcher() -> FakeFetcher:
    return FakeFetcher(blocked=frozenset({BLOCKED_URL}))


@pytest.fixture()
def recording_email() -> RecordingEmailSender:
    return RecordingEmailSender()


@pytest.fixture()
def client(
    db_session: Session, fake_fetcher: FakeFetcher, recording_email: RecordingEmailSender
) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = InMemoryStorage
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(EXTRACTION_JSON), max_retries=1
    )
    app.dependency_overrides[get_fetcher] = lambda: fake_fetcher
    app.dependency_overrides[get_email_sender] = lambda: recording_email
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
