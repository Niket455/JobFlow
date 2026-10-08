import json

from app.adapters.base import FetchError, FetchResult, RobotsDisallowedError

DE_URL = "https://jobs.example.com/data-engineer"
MIRROR_URL = "https://mirror.example.com/roles/42"
REMOTE_URL = "https://jobs.example.com/data-engineer-remote"
HTML_URL = "https://careers.example.com/html-only"
BLOCKED_URL = "https://blocked.example/job"
DOWN_URL = "https://down.example/job"


def jsonld_page(
    title: str,
    company: str,
    location: str,
    description: str,
    *,
    valid_through: str | None = None,
) -> str:
    posting: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "hiringOrganization": {"@type": "Organization", "name": company},
        "jobLocation": {
            "@type": "Place",
            "address": {"@type": "PostalAddress", "addressLocality": location},
        },
        "description": f"<p>{description}</p>",
    }
    if valid_through is not None:
        posting["validThrough"] = valid_through
    script = json.dumps(posting)
    return (
        "<html><head>"
        f'<script type="application/ld+json">{script}</script>'
        f"</head><body><p>{description}</p></body></html>"
    )


def html_only_page(title: str, body: str) -> str:
    return (
        f"<html><head><title>{title}</title></head>"
        f"<body><h1>{title}</h1><p>{body}</p></body></html>"
    )


def default_pages() -> dict[str, str]:
    return {
        DE_URL: jsonld_page("Data Engineer", "Acme Inc", "Bengaluru", "Build data pipelines."),
        MIRROR_URL: jsonld_page("Data Engineer", "Acme Inc", "Bengaluru", "Build data pipelines."),
        REMOTE_URL: jsonld_page("Data Engineer", "Acme Inc", "Remote", "Build data pipelines."),
        HTML_URL: html_only_page("Backend Engineer", "We use Python and Postgres."),
    }


class FakeFetcher:
    """Offline stand-in for the real fetcher, keyed by URL."""

    def __init__(
        self, pages: dict[str, str] | None = None, *, blocked: frozenset[str] = frozenset()
    ) -> None:
        self.pages = dict(pages) if pages is not None else default_pages()
        self.blocked = set(blocked)

    def fetch(self, url: str) -> FetchResult:
        if url in self.blocked:
            raise RobotsDisallowedError(url)
        text = self.pages.get(url)
        if text is None:
            raise FetchError(url, "not found", status_code=404)
        return FetchResult(url=url, status_code=200, text=text)
