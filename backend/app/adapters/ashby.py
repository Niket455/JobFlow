import re
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.adapters.base import FetchError, FetchResult
from app.adapters.http_json import get_json
from app.adapters.jsonld import job_posting, to_jsonld_result
from app.adapters.mapping import as_text, humanize_token, postal_location

API_BASE = "https://api.ashbyhq.com/posting-api/job-board"
BOARD_PATH = re.compile(r"^/(?P<org>[^/]+)(?:/(?P<job_id>[^/]+))?/?$")


class AshbyAdapter:
    """Fetch a single Ashby posting from the public Job Postings API (board list + match)."""

    name = "ashby"

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def matches(self, url: str) -> bool:
        parsed = self._parse(url)
        return parsed is not None and parsed[1] is not None

    def fetch(self, url: str) -> FetchResult:
        parsed = self._parse(url)
        if parsed is None:
            raise FetchError(url, "not an Ashby job URL")
        org, job_id = parsed
        if job_id is None:
            raise FetchError(url, "not an Ashby job URL")
        data = get_json(self._client, f"{API_BASE}/{org}")
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            raise FetchError(url, "unexpected Ashby response")
        job = _select(jobs, url, job_id)
        if job is None:
            raise FetchError(url, "job not found on the Ashby board")
        title = as_text(job.get("title"))
        if not title:
            raise FetchError(url, "Ashby posting has no title")
        canonical_url = as_text(job.get("jobUrl")) or url
        posting = job_posting(
            title=title,
            company_name=humanize_token(org),
            location=as_text(job.get("location")) or postal_location(job.get("address")),
            description=as_text(job.get("descriptionPlain")) or as_text(job.get("descriptionHtml")),
            external_id=_external_id(canonical_url) or job_id,
            url=canonical_url,
        )
        return to_jsonld_result(posting, url=canonical_url, adapter=self.name)

    @staticmethod
    def _parse(url: str) -> tuple[str, str | None] | None:
        parts = urlsplit(url)
        if (parts.hostname or "") != "jobs.ashbyhq.com":
            return None
        match = BOARD_PATH.match(parts.path)
        if match is None:
            return None
        return match.group("org"), match.group("job_id")


def _select(jobs: list[Any], url: str, job_id: str) -> dict[str, Any] | None:
    target = _path(url)
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_url = as_text(job.get("jobUrl"))
        if job_url and (_path(job_url) == target or _path(job_url).endswith(f"/{job_id}")):
            return job
    return None


def _path(url: str) -> str:
    return urlsplit(url).path.rstrip("/")


def _external_id(job_url: str) -> str | None:
    segments = _path(job_url).rsplit("/", 1)
    return segments[-1] or None
