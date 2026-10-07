from fastapi.testclient import TestClient

REGISTER = {"email": "jane@example.com", "password": "supersecret1"}


def _register(client: TestClient):
    return client.post("/api/v1/auth/register", json=REGISTER)


def test_register_returns_user(client: TestClient) -> None:
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == REGISTER["email"]
    assert "id" in body
    assert "password" not in body


def test_register_duplicate_conflict(client: TestClient) -> None:
    _register(client)
    assert _register(client).status_code == 409


def test_login_and_me(client: TestClient) -> None:
    _register(client)
    login = client.post("/api/v1/auth/login", json=REGISTER)
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"

    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == REGISTER["email"]


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_wrong_password(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_refresh_issues_new_tokens(client: TestClient) -> None:
    _register(client)
    tokens = client.post("/api/v1/auth/login", json=REGISTER).json()
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
