import io

from docx import Document
from fastapi.testclient import TestClient

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USER = {"email": "resume@example.com", "password": "supersecret1"}


def _headers(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=USER)
    tokens = client.post("/api/v1/auth/login", json=USER).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _upload(client: TestClient, headers: dict[str, str], filename: str = "resume.docx"):
    files = {"file": (filename, _docx_bytes("Jane Doe Python SQL"), DOCX_CONTENT_TYPE)}
    return client.post("/api/v1/resumes", files=files, headers=headers)


def test_upload_requires_auth(client: TestClient) -> None:
    files = {"file": ("resume.docx", _docx_bytes("x"), DOCX_CONTENT_TYPE)}
    assert client.post("/api/v1/resumes", files=files).status_code == 401


def test_upload_creates_master_and_parses(client: TestClient) -> None:
    headers = _headers(client)
    response = _upload(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["is_master"] is True
    assert body["label"] == "Master"
    assert body["parsed"]["full_name"] == "Jane Doe"
    assert body["parsed"]["skills"] == ["Python", "SQL", "PySpark"]
    assert body["confidence"]["skills"] == 0.8


def test_second_upload_is_new_version(client: TestClient) -> None:
    headers = _headers(client)
    _upload(client, headers)
    second = _upload(client, headers)
    assert second.status_code == 201
    body = second.json()
    assert body["is_master"] is False
    assert body["label"] == "Version 2"


def test_rejects_unsupported_type(client: TestClient) -> None:
    headers = _headers(client)
    files = {"file": ("resume.txt", b"plain text", "text/plain")}
    response = client.post("/api/v1/resumes", files=files, headers=headers)
    assert response.status_code == 415


def test_list_and_get(client: TestClient) -> None:
    headers = _headers(client)
    created = _upload(client, headers).json()

    listing = client.get("/api/v1/resumes", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["label"] == "Master"

    detail = client.get(f"/api/v1/resumes/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["parsed"]["full_name"] == "Jane Doe"


def test_resumes_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client)
    _upload(client, headers_a)

    other = {"email": "other@example.com", "password": "supersecret9"}
    client.post("/api/v1/auth/register", json=other)
    tokens = client.post("/api/v1/auth/login", json=other).json()
    headers_b = {"Authorization": f"Bearer {tokens['access_token']}"}

    assert client.get("/api/v1/resumes", headers=headers_b).json() == []
