from fastapi.testclient import TestClient

USER_A = {"email": "a@example.com", "password": "supersecret1"}
USER_B = {"email": "b@example.com", "password": "supersecret2"}


def _auth_headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_profile_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/profile").status_code == 401
    assert client.put("/api/v1/profile", json={}).status_code == 401


def test_profile_round_trip(client: TestClient) -> None:
    headers = _auth_headers(client, USER_A)

    empty = client.get("/api/v1/profile", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["skills"] == []

    payload = {
        "full_name": "Jane Doe",
        "phone": "+91 90000 00000",
        "skills": ["Python", "SQL"],
        "work_history": [{"company": "Acme", "title": "Data Engineer"}],
    }
    saved = client.put("/api/v1/profile", json=payload, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["full_name"] == "Jane Doe"

    fetched = client.get("/api/v1/profile", headers=headers)
    assert fetched.json()["full_name"] == "Jane Doe"
    assert fetched.json()["skills"] == ["Python", "SQL"]
    assert fetched.json()["work_history"][0]["company"] == "Acme"


def test_profile_is_isolated_per_user(client: TestClient) -> None:
    headers_a = _auth_headers(client, USER_A)
    headers_b = _auth_headers(client, USER_B)

    client.put("/api/v1/profile", json={"full_name": "Alice"}, headers=headers_a)

    profile_b = client.get("/api/v1/profile", headers=headers_b)
    assert profile_b.status_code == 200
    assert profile_b.json()["full_name"] is None


def test_career_goal_round_trip(client: TestClient) -> None:
    headers = _auth_headers(client, USER_A)

    empty = client.get("/api/v1/career-goals", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["target_role"] is None

    payload = {
        "target_role": "AI Engineer",
        "target_salary_min": 1500000,
        "locations": ["Bengaluru", "Hyderabad"],
    }
    saved = client.put("/api/v1/career-goals", json=payload, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["target_role"] == "AI Engineer"

    fetched = client.get("/api/v1/career-goals", headers=headers)
    assert fetched.json()["target_salary_min"] == 1500000
    assert fetched.json()["locations"] == ["Bengaluru", "Hyderabad"]


def test_deal_breakers_round_trip(client: TestClient) -> None:
    headers = _auth_headers(client, USER_A)

    payload = {
        "min_salary": 800000,
        "excluded_companies": ["Acme"],
        "no_night_shifts": True,
    }
    saved = client.put("/api/v1/deal-breakers", json=payload, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["no_night_shifts"] is True

    fetched = client.get("/api/v1/deal-breakers", headers=headers)
    assert fetched.json()["excluded_companies"] == ["Acme"]
    assert fetched.json()["min_salary"] == 800000
