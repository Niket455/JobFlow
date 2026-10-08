import html
import json
from typing import Any

from app.adapters.base import FetchResult

SCHEMA_CONTEXT = "https://schema.org"


def unescape_html(value: str | None) -> str:
    """Greenhouse returns the job content double-HTML-escaped; unescape twice to recover it."""
    if not value:
        return ""
    return html.unescape(html.unescape(value))


def job_posting(
    *,
    title: str,
    company_name: str | None = None,
    location: str | None = None,
    description: str | None = None,
    external_id: str | None = None,
    valid_through: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Build a schema.org JobPosting — the interchange shape `job_normalizer.normalize` consumes."""
    posting: dict[str, Any] = {
        "@context": SCHEMA_CONTEXT,
        "@type": "JobPosting",
        "title": title,
    }
    if company_name:
        posting["hiringOrganization"] = {"@type": "Organization", "name": company_name}
    if location:
        posting["jobLocation"] = {
            "@type": "Place",
            "address": {"@type": "PostalAddress", "addressLocality": location},
        }
    if description:
        posting["description"] = description
    if external_id is not None:
        posting["identifier"] = {"@type": "PropertyValue", "value": str(external_id)}
    if valid_through:
        posting["validThrough"] = valid_through
    if url:
        posting["url"] = url
    return posting


def to_jsonld_result(
    posting: dict[str, Any],
    *,
    url: str,
    adapter: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """Wrap a JobPosting as a minimal HTML document with one JSON-LD script block."""
    payload = json.dumps(posting).replace("</", "<\\/")
    text = (
        "<!doctype html><html><head>"
        f'<script type="application/ld+json">{payload}</script>'
        "</head><body></body></html>"
    )
    return FetchResult(
        url=url,
        status_code=status_code,
        text=text,
        headers=headers or {"content-type": "text/html; charset=utf-8"},
        adapter=adapter,
    )
