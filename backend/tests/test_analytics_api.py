from fake_fetcher import DE_URL, REMOTE_URL
from fastapi.testclient import TestClient

USER_A = {"email": "analytics-a@example.com", "password": "supersecret1"}
USER_B = {"email": "analytics-b@example.com", "password": "supersecret2"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _apply(
    client: TestClient,
    headers: dict[str, str],
    url: str,
    *,
    source: str = "linkedin",
    events: tuple[dict, ...] = (),
    applied_at: str | None = None,
) -> dict:
    job = client.post("/api/v1/jobs", json={"url": url}, headers=headers).json()
    payload: dict[str, object] = {"job_id": job["id"], "source": source}
    if applied_at is not None:
        payload["applied_at"] = applied_at
    application = client.post("/api/v1/applications", json=payload, headers=headers).json()
    for event in events:
        client.post(f"/api/v1/applications/{application['id']}/events", json=event, headers=headers)
    return application


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/analytics/funnel").status_code == 401
    assert client.get("/api/v1/analytics/rates").status_code == 401
    assert client.get("/api/v1/analytics/rejections").status_code == 401
    assert client.get("/api/v1/analytics/rejection-reasons").status_code == 401


def test_funnel_and_rates(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _apply(client, headers, DE_URL, events=({"type": "applied"}, {"type": "interview"}))

    funnel = client.get("/api/v1/analytics/funnel", headers=headers).json()
    counts = {stage["stage"]: stage["count"] for stage in funnel["stages"]}
    assert funnel["total"] == 1
    assert counts["applied"] == 1
    assert counts["interview"] == 1
    assert counts["offer"] == 0

    metrics = client.get("/api/v1/analytics/rates", headers=headers).json()
    assert metrics["interview"]["numerator"] == 1
    assert metrics["interview"]["denominator"] == 1
    assert metrics["interview"]["value"] == 1.0
    assert metrics["interview"]["sufficient_sample"] is False


def test_rejections_breakdown(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _apply(
        client,
        headers,
        DE_URL,
        source="linkedin",
        events=({"type": "applied"}, {"type": "rejected", "payload": {"reason": "no response"}}),
    )
    _apply(client, headers, REMOTE_URL, source="referral", events=({"type": "applied"},))

    report = client.get("/api/v1/analytics/rejections?by=source", headers=headers).json()
    assert report["by"] == "source"
    assert report["total_rejected"] == 1
    buckets = {bucket["key"]: bucket for bucket in report["buckets"]}
    assert buckets["linkedin"]["rejected"] == 1
    assert buckets["referral"]["rejected"] == 0
    assert buckets["referral"]["rate"] is None  # below min sample
    assert "no response" in report["reasons"]


def test_rejections_rejects_unknown_dimension(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert client.get("/api/v1/analytics/rejections?by=banana", headers=headers).status_code == 422


def test_analytics_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    _apply(client, headers_a, DE_URL, events=({"type": "applied"},))

    headers_b = _headers(client, USER_B)
    funnel = client.get("/api/v1/analytics/funnel", headers=headers_b).json()
    assert funnel["total"] == 0
    assert all(stage["count"] == 0 for stage in funnel["stages"])


def test_funnel_breakdown_by_source(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _apply(
        client,
        headers,
        DE_URL,
        source="linkedin",
        events=({"type": "applied"}, {"type": "interview"}),
    )
    _apply(client, headers, REMOTE_URL, source="referral", events=({"type": "applied"},))

    funnel = client.get("/api/v1/analytics/funnel?by=source", headers=headers).json()

    assert funnel["by"] == "source"
    buckets = {bucket["key"]: bucket for bucket in funnel["buckets"]}
    assert set(buckets) == {"linkedin", "referral"}
    linkedin = {stage["stage"]: stage["count"] for stage in buckets["linkedin"]["stages"]}
    assert linkedin["interview"] == 1
    assert buckets["referral"]["total"] == 1


def test_rates_breakdown_by_source(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _apply(
        client,
        headers,
        DE_URL,
        source="linkedin",
        events=({"type": "applied"}, {"type": "interview"}),
    )

    rates = client.get("/api/v1/analytics/rates?by=source", headers=headers).json()

    buckets = {bucket["key"]: bucket for bucket in rates["buckets"]}
    assert buckets["linkedin"]["interview"]["numerator"] == 1


def test_breakdown_rejects_unknown_dimension(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert client.get("/api/v1/analytics/funnel?by=banana", headers=headers).status_code == 422
    assert client.get("/api/v1/analytics/rates?by=banana", headers=headers).status_code == 422


def test_period_filter_limits_the_funnel(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _apply(client, headers, DE_URL, applied_at="2026-01-01T00:00:00Z")
    _apply(client, headers, REMOTE_URL, applied_at="2026-06-01T00:00:00Z")

    assert client.get("/api/v1/analytics/funnel", headers=headers).json()["total"] == 2
    filtered = client.get(
        "/api/v1/analytics/funnel?since=2025-12-01&until=2026-03-01", headers=headers
    ).json()
    assert filtered["total"] == 1


def test_rejection_reasons_breakdown(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _apply(
        client,
        headers,
        DE_URL,
        events=({"type": "applied"}, {"type": "rejected", "payload": {"reason": "no_response"}}),
    )
    _apply(client, headers, REMOTE_URL, events=({"type": "applied"}, {"type": "rejected"}))

    report = client.get("/api/v1/analytics/rejection-reasons", headers=headers).json()

    assert report["total_rejected"] == 2
    assert "no_response" in report["catalog"]
    counts = {item["reason"]: item["count"] for item in report["reasons"]}
    assert counts["no_response"] == 1
    assert report["uncategorized"] == 1
