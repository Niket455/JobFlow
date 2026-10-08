import uuid

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.contact import Contact

USER_A = {"email": "crm-a@example.com", "password": "supersecret1"}
USER_B = {"email": "crm-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create(client: TestClient, headers: dict[str, str], **extra: object) -> dict:
    body = {"name": "Sam Recruiter", "relationship": "referral", **extra}
    response = client.post("/api/v1/contacts", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_contacts_require_auth(client: TestClient) -> None:
    assert client.post("/api/v1/contacts", json={"name": "x"}).status_code == 401


def test_contact_crud(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    contact = _create(client, headers, title="Talent Partner", company_name="Acme")

    listed = client.get("/api/v1/contacts", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == contact["id"]
    assert "notes" not in listed[0]

    fetched = client.get(f"/api/v1/contacts/{contact['id']}", headers=headers).json()
    assert fetched["title"] == "Talent Partner"

    updated = client.put(
        f"/api/v1/contacts/{contact['id']}",
        json={"relationship": "hiring_manager"},
        headers=headers,
    ).json()
    assert updated["relationship"] == "hiring_manager"
    assert updated["name"] == "Sam Recruiter"

    assert client.delete(f"/api/v1/contacts/{contact['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/contacts/{contact['id']}", headers=headers).status_code == 404


def test_notes_are_encrypted(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    contact = _create(client, headers, notes="Met at a meetup; warm intro possible.")

    assert contact["notes"] == "Met at a meetup; warm intro possible."
    row = db_session.get(Contact, uuid.UUID(contact["id"]))
    assert row is not None
    assert row.notes_enc is not None
    assert row.notes_enc != contact["notes"]


def test_company_link_validated(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)

    bad = client.post(
        "/api/v1/contacts", json={"name": "X", "company_id": UNKNOWN}, headers=headers
    )
    assert bad.status_code == 400

    client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers)
    company = db_session.scalar(select(Company))
    assert company is not None
    linked = _create(client, headers, company_id=str(company.id))
    assert linked["company_id"] == str(company.id)


def test_contacts_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    contact = _create(client, headers_a)

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/contacts", headers=headers_b).json() == []
    assert client.get(f"/api/v1/contacts/{contact['id']}", headers=headers_b).status_code == 404
