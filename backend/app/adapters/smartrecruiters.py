import html
import re
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.adapters.base import FetchError, FetchResult
from app.adapters.http_json import get_json
from app.adapters.jsonld import job_posting, to_jsonld_result
from app.adapters.mapping import as_text, humanize_token

API_BASE = "https://api.smartrecruiters.com/v1/companies"
HOSTS = {"jobs.smartrecruiters.com", "careers.smartrecruiters.com"}
_PATH = re.compile(r"^/(?P<company>[^/]+)/(?P<segment>[^/]+)/?$")
_ID = re.compile(r"^(\d+)")

_SECTION_ORDER = (
    "companyDescription",
    "jobDescription",
    "qualifications",
    "additionalInformation",
)


class SmartRecruitersAdapter:
    """Fetch a single SmartRecruiters posting from the public Posting API."""

    name = "smartrecruiters"

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def matches(self, url: str) -> bool:
        return self._parse(url) is not None

    def fetch(self, url: str) -> FetchResult:
        parsed = self._parse(url)
        if parsed is None:
            raise FetchError(url, "not a SmartRecruiters job URL")
        company, posting_id = parsed
        data = get_json(self._client, f"{API_BASE}/{company}/postings/{posting_id}")
        if not isinstance(data, dict):
            raise FetchError(url, "unexpected SmartRecruiters response")
        title = as_text(data.get("name"))
        if not title:
            raise FetchError(url, "SmartRecruiters posting has no title")
        posting = job_posting(
            title=title,
            company_name=_company_name(data, company),
            location=_location(data.get("location")),
            description=_description(data.get("jobAd")),
            external_id=as_text(data.get("id")) or posting_id,
            url=url,
        )
        return to_jsonld_result(posting, url=url, adapter=self.name)

    @staticmethod
    def _parse(url: str) -> tuple[str, str] | None:
        parts = urlsplit(url)
        if (parts.hostname or "") not in HOSTS:
            return None
        match = _PATH.match(parts.path)
        if match is None:
            return None
        posting_id = _ID.match(match.group("segment"))
        if posting_id is None:
            return None
        return match.group("company"), posting_id.group(1)


def _company_name(data: dict[str, Any], company: str) -> str:
    company_data = data.get("company")
    if isinstance(company_data, dict):
        name = as_text(company_data.get("name"))
        if name:
            return name
    return humanize_token(company)


def _location(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    parts = [as_text(value.get(key)) for key in ("city", "region", "country")]
    joined = ", ".join(part for part in parts if part)
    if value.get("remote"):
        return f"{joined} (Remote)" if joined else "Remote"
    return joined or None


def _description(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    sections = value.get("sections")
    if not isinstance(sections, dict):
        return ""
    texts: list[str] = []
    for key in _SECTION_ORDER:
        section = sections.get(key)
        if isinstance(section, dict):
            text = as_text(section.get("text"))
            if text:
                texts.append(html.unescape(text))
    return "\n\n".join(texts)
