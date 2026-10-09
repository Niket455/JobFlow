import io

from docx import Document
from fake_fetcher import DE_URL
from fastapi.testclient import TestClient

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USER_A = {"email": "atsrep-a@example.com", "password": "supersecret1"}
USER_B = {"email": "atsrep-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _upload_resume(client: TestClient, headers: dict[str, str]) -> str:
    files = {"file": ("resume.docx", _docx_bytes("Jane Doe Python SQL"), DOCX_CONTENT_TYPE)}
    response = client.post("/api/v1/resumes", files=files, headers=headers)
    assert response.status_code == 201
    return str(response.json()["id"])


def _ingest(client: TestClient, headers: dict[str, str]) -> str:
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    return str(job["id"])


def test_requires_auth(client: TestClient) -> None:
    assert client.post(f"/api/v1/resumes/{UNKNOWN}/ats-report", json={}).status_code == 401
    assert client.get("/api/v1/ats-reports").status_code == 401
    assert client.get(f"/api/v1/ats-reports/{UNKNOWN}").status_code == 401


def test_persist_list_and_get(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)

    created = client.post(f"/api/v1/resumes/{resume_id}/ats-report", json={}, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["resume_version_id"] == resume_id
    assert body["job_id"] is None
    assert body["score"] == body["report"]["score"]
    assert body["grade"] in {"A", "B", "C", "D", "F"}
    assert any(check["id"] == "parse_docx" for check in body["report"]["checks"])

    listed = client.get("/api/v1/ats-reports", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]
    assert "report" not in listed[0]

    fetched = client.get(f"/api/v1/ats-reports/{body['id']}", headers=headers).json()
    assert fetched["report"]["score"] == body["score"]


def test_read_does_not_persist(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)

    assert client.get(f"/api/v1/resumes/{resume_id}/ats-report", headers=headers).status_code == 200
    assert client.get("/api/v1/ats-reports", headers=headers).json() == []


def test_list_filters_by_resume(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    client.post(f"/api/v1/resumes/{resume_id}/ats-report", json={}, headers=headers)

    matching = client.get(
        f"/api/v1/ats-reports?resume_version_id={resume_id}", headers=headers
    ).json()
    assert len(matching) == 1
    assert (
        client.get(f"/api/v1/ats-reports?resume_version_id={UNKNOWN}", headers=headers).json() == []
    )


def test_reports_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers_a)
    report = client.post(
        f"/api/v1/resumes/{resume_id}/ats-report", json={}, headers=headers_a
    ).json()

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/ats-reports", headers=headers_b).json() == []
    assert client.get(f"/api/v1/ats-reports/{report['id']}", headers=headers_b).status_code == 404


def test_unknown_resume_and_foreign_job_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert (
        client.post(f"/api/v1/resumes/{UNKNOWN}/ats-report", json={}, headers=headers).status_code
        == 404
    )

    job_id = _ingest(client, headers)
    headers_b = _headers(client, USER_B)
    resume_b = _upload_resume(client, headers_b)
    response = client.post(
        f"/api/v1/resumes/{resume_b}/ats-report", json={"job_id": job_id}, headers=headers_b
    )
    assert response.status_code == 404
