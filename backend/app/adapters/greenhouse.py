import re
from urllib.parse import urlsplit

import httpx

from app.adapters.base import FetchError, FetchResult
from app.adapters.http_json import get_json
from app.adapters.jsonld import job_posting, to_jsonld_result, unescape_html
from app.adapters.mapping import as_text, named_value

API_BASE = "https://boards-api.greenhouse.io/v1/boards"
HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io"}
_JOB_PATH = re.compile(r"^/(?P<token>[^/]+)/jobs/(?P<job_id>\d+)/?$")


class GreenhouseAdapter:
    """Fetch a single Greenhouse job from the public Job Board API."""

    name = "greenhouse"

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def matches(self, url: str) -> bool:
        return self._parse(url) is not None

    def fetch(self, url: str) -> FetchResult:
        parsed = self._parse(url)
        if parsed is None:
            raise FetchError(url, "not a Greenhouse job URL")
        token, job_id = parsed
        data = get_json(self._client, f"{API_BASE}/{token}/jobs/{job_id}")
        if not isinstance(data, dict):
            raise FetchError(url, "unexpected Greenhouse response")
        title = as_text(data.get("title"))
        if not title:
            raise FetchError(url, "Greenhouse job has no title")
        canonical_url = as_text(data.get("absolute_url")) or url
        posting = job_posting(
            title=title,
            company_name=as_text(data.get("company_name")) or token,
            location=named_value(data.get("location")),
            description=unescape_html(as_text(data.get("content"))),
            external_id=as_text(data.get("id")) or job_id,
            valid_through=as_text(data.get("application_deadline")),
            url=canonical_url,
        )
        return to_jsonld_result(posting, url=canonical_url, adapter=self.name)

    @staticmethod
    def _parse(url: str) -> tuple[str, str] | None:
        parts = urlsplit(url)
        if (parts.hostname or "") not in HOSTS:
            return None
        match = _JOB_PATH.match(parts.path)
        if match is None:
            return None
        return match.group("token"), match.group("job_id")
