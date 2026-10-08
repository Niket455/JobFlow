import re
from urllib.parse import urlsplit

import httpx

from app.adapters.base import FetchError, FetchResult
from app.adapters.http_json import get_json
from app.adapters.jsonld import job_posting, to_jsonld_result
from app.adapters.mapping import as_text, humanize_token

API_BASE = "https://api.lever.co/v0/postings"
API_BASE_EU = "https://api.eu.lever.co/v0/postings"
POSTING_PATH = re.compile(r"^/(?P<site>[^/]+)/(?P<posting_id>[0-9a-fA-F-]+)(?:/apply)?/?$")


class LeverAdapter:
    """Fetch a single Lever posting from the public Postings API."""

    name = "lever"

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def matches(self, url: str) -> bool:
        return self._parse(url) is not None

    def fetch(self, url: str) -> FetchResult:
        parsed = self._parse(url)
        if parsed is None:
            raise FetchError(url, "not a Lever posting URL")
        base, site, posting_id = parsed
        data = get_json(self._client, f"{base}/{site}/{posting_id}?mode=json")
        if not isinstance(data, dict):
            raise FetchError(url, "unexpected Lever response")
        title = as_text(data.get("text"))
        if not title:
            raise FetchError(url, "Lever posting has no title")
        categories = data.get("categories")
        location = as_text(categories.get("location")) if isinstance(categories, dict) else None
        canonical_url = as_text(data.get("hostedUrl")) or url
        posting = job_posting(
            title=title,
            company_name=humanize_token(site),
            location=location,
            description=as_text(data.get("descriptionPlain")) or as_text(data.get("description")),
            external_id=as_text(data.get("id")) or posting_id,
            url=canonical_url,
        )
        return to_jsonld_result(posting, url=canonical_url, adapter=self.name)

    @staticmethod
    def _parse(url: str) -> tuple[str, str, str] | None:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if host == "jobs.lever.co":
            base = API_BASE
        elif host == "jobs.eu.lever.co":
            base = API_BASE_EU
        else:
            return None
        match = POSTING_PATH.match(parts.path)
        if match is None:
            return None
        return base, match.group("site"), match.group("posting_id")
