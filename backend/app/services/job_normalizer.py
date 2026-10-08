import json
import re
from dataclasses import dataclass, field
from typing import Any, cast

from bs4 import BeautifulSoup

from app.adapters.base import FetchResult

MAX_RAW_CHARS = 200_000


@dataclass
class NormalizedJob:
    title: str
    company_name: str | None
    location: str | None
    description: str
    external_id: str | None = None
    valid_through: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def normalize(result: FetchResult) -> NormalizedJob:
    """Extract a structured job from a fetched page: schema.org JSON-LD first, HTML fallback."""
    soup = BeautifulSoup(result.text, "html.parser")
    posting = _find_job_posting(soup)
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return _build(posting, soup, result)


def _build(posting: dict[str, Any] | None, soup: Any, result: FetchResult) -> NormalizedJob:
    title = (
        _first_text(_get(posting, "title"), _meta_content(soup, "og:title"), _title_tag(soup))
        or result.url
    )
    raw = (
        {"json_ld": posting}
        if posting is not None
        else {"text": _visible_text(soup)[:MAX_RAW_CHARS]}
    )
    return NormalizedJob(
        title=title,
        company_name=_organization_name(_get(posting, "hiringOrganization")),
        location=_location_text(_get(posting, "jobLocation")),
        description=_html_to_text(_get(posting, "description")) or _visible_text(soup),
        external_id=_external_id(posting),
        valid_through=_first_text(_get(posting, "validThrough")),
        raw=raw,
    )


def _get(data: dict[str, Any] | None, key: str) -> Any:
    return data.get(key) if data is not None else None


def _find_job_posting(soup: Any) -> dict[str, Any] | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            parsed = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        posting = _first_job_posting(parsed)
        if posting is not None:
            return posting
    return None


def _first_job_posting(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict):
        if data.get("@type") == "JobPosting":
            return cast(dict[str, Any], data)
        for value in data.values():
            found = _first_job_posting(value)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _first_job_posting(item)
            if found is not None:
                return found
    return None


def _organization_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return _first_text(value.get("name"), value.get("legalName"))
    if isinstance(value, list):
        for item in value:
            name = _organization_name(item)
            if name:
                return name
    return _as_text(value)


def _location_text(value: Any) -> str | None:
    if isinstance(value, dict):
        address = value.get("address")
        if isinstance(address, dict):
            parts = [
                _address_part(address.get(key))
                for key in ("addressLocality", "addressRegion", "addressCountry")
            ]
            joined = ", ".join(part for part in parts if part)
            return joined or _as_text(address.get("streetAddress"))
        return _first_text(value.get("name"), _as_text(address))
    if isinstance(value, list):
        locations = [loc for loc in (_location_text(item) for item in value) if loc]
        return "; ".join(locations) or None
    return _as_text(value)


def _address_part(value: Any) -> str | None:
    if isinstance(value, dict):
        return _first_text(value.get("name"))
    return _as_text(value)


def _external_id(posting: dict[str, Any] | None) -> str | None:
    if posting is None:
        return None
    identifier = posting.get("identifier")
    if isinstance(identifier, dict):
        return _first_text(identifier.get("value"), identifier.get("name"))
    return _first_text(identifier, posting.get("@id"))


def _html_to_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return _collapse(BeautifulSoup(value, "html.parser").get_text(" ")) or None


def _visible_text(soup: Any) -> str:
    return _collapse(soup.get_text(" "))


def _meta_content(soup: Any, prop: str) -> str | None:
    meta = soup.find("meta", attrs={"property": prop})
    if meta is None:
        return None
    return _as_text(meta.get("content"))


def _title_tag(soup: Any) -> str | None:
    if soup.title is not None:
        return _as_text(soup.title.string)
    return None


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _as_text(value)
        if text:
            return text
    return None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return _collapse(value) or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
