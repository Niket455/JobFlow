from fake_fetcher import html_only_page, jsonld_page

from app.adapters.base import FetchResult
from app.services.job_normalizer import normalize


def _result(text: str) -> FetchResult:
    return FetchResult(url="https://example.com/job", status_code=200, text=text)


def test_extracts_jsonld_jobposting() -> None:
    page = jsonld_page("Data Engineer", "Acme Inc", "Bengaluru", "Build <b>pipelines</b>.")
    job = normalize(_result(page))
    assert job.title == "Data Engineer"
    assert job.company_name == "Acme Inc"
    assert job.location == "Bengaluru"
    assert "pipelines" in job.description
    assert "<b>" not in job.description
    assert job.raw["json_ld"]["@type"] == "JobPosting"


def test_html_fallback_uses_title() -> None:
    page = html_only_page("Backend Engineer", "We use Python and Postgres.")
    job = normalize(_result(page))
    assert job.title == "Backend Engineer"
    assert job.company_name is None
    assert "Python" in job.description


def test_preserves_valid_through() -> None:
    page = jsonld_page("DE", "Acme", "Remote", "text", valid_through="2020-01-01")
    job = normalize(_result(page))
    assert job.valid_through == "2020-01-01"
