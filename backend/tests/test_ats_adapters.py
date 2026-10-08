from fake_fetcher import (
    ASHBY_URL,
    GH_URL,
    LEVER_URL,
    ats_client,
)

from app.adapters.ashby import AshbyAdapter
from app.adapters.base import Adapter, FetchResult
from app.adapters.dispatch import DispatchFetcher
from app.adapters.greenhouse import GreenhouseAdapter
from app.adapters.lever import LeverAdapter
from app.services.job_normalizer import normalize


class _StubFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        return FetchResult(url=url, status_code=200, text="<html></html>", adapter="user_url")


def test_greenhouse_adapter_maps_job() -> None:
    adapter = GreenhouseAdapter(ats_client())
    assert adapter.matches(GH_URL)
    assert not adapter.matches("https://boards.greenhouse.io/vaulttec")

    result = adapter.fetch(GH_URL)
    assert result.adapter == "greenhouse"

    job = normalize(result)
    assert job.title == "Vault Designer"
    assert job.company_name == "Vault Tec"
    assert job.location == "NYC"
    assert job.description == "Design vaults."  # double-escaped content recovered
    assert job.external_id == "127817"
    assert job.valid_through == "2030-01-01T00:00:00Z"


def test_lever_adapter_maps_job() -> None:
    adapter = LeverAdapter(ats_client())
    assert adapter.matches(LEVER_URL)

    result = adapter.fetch(LEVER_URL)
    assert result.adapter == "lever"
    job = normalize(result)
    assert job.title == "Backend Engineer"
    assert job.company_name == "Leverdemo"
    assert job.location == "Bengaluru"
    assert job.description == "Build services."
    assert job.external_id == "5ac21346-8e0c-4494-8e7a-3eb92ff77902"


def test_lever_adapter_matches_eu_host() -> None:
    url = "https://jobs.eu.lever.co/leverdemo/5ac21346-8e0c-4494-8e7a-3eb92ff77902"
    assert LeverAdapter(ats_client()).matches(url)


def test_ashby_adapter_selects_matching_posting() -> None:
    adapter = AshbyAdapter(ats_client())
    assert adapter.matches(ASHBY_URL)
    assert not adapter.matches("https://jobs.ashbyhq.com/acme")  # board URL, no job id

    result = adapter.fetch(ASHBY_URL)
    assert result.adapter == "ashby"
    job = normalize(result)
    assert job.title == "Product Manager"
    assert job.company_name == "Acme"
    assert job.location == "Houston, TX"
    assert job.description == "Own the roadmap."
    assert job.external_id == "abc-123"


def test_adapters_ignore_unrelated_hosts() -> None:
    client = ats_client()
    for adapter in (GreenhouseAdapter(client), LeverAdapter(client), AshbyAdapter(client)):
        assert not adapter.matches("https://jobs.example.com/data-engineer")


def test_dispatch_uses_adapter_when_matched() -> None:
    fallback = _StubFetcher()
    adapters: list[Adapter] = [GreenhouseAdapter(ats_client())]
    dispatch = DispatchFetcher(adapters, fallback)

    result = dispatch.fetch(GH_URL)
    assert result.adapter == "greenhouse"
    assert fallback.calls == []


def test_dispatch_falls_back_on_adapter_error() -> None:
    fallback = _StubFetcher()
    adapters: list[Adapter] = [GreenhouseAdapter(ats_client())]
    dispatch = DispatchFetcher(adapters, fallback)

    # A matching host whose API returns 404 → adapter raises FetchError → generic fallback.
    url = "https://boards.greenhouse.io/vaulttec/jobs/999999"
    result = dispatch.fetch(url)
    assert result.adapter == "user_url"
    assert fallback.calls == [url]


def test_dispatch_falls_back_for_unknown_host() -> None:
    fallback = _StubFetcher()
    dispatch = DispatchFetcher([], fallback)

    url = "https://careers.example.com/html-only"
    assert dispatch.fetch(url).adapter == "user_url"
    assert fallback.calls == [url]
