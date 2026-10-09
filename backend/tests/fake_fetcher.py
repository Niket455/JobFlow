import json

import httpx

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


# --- ATS public-API fixtures (Greenhouse / Lever / Ashby) --------------------------------

GH_URL = "https://boards.greenhouse.io/vaulttec/jobs/127817"
GH_API = "https://boards-api.greenhouse.io/v1/boards/vaulttec/jobs/127817"
GH_JSON = {
    "id": 127817,
    "title": "Vault Designer",
    "company_name": "Vault Tec",
    "location": {"name": "NYC"},
    "content": "&amp;lt;p&amp;gt;Design vaults.&amp;lt;/p&amp;gt;",
    "absolute_url": GH_URL,
    "application_deadline": "2030-01-01T00:00:00Z",
}

LEVER_URL = "https://jobs.lever.co/leverdemo/5ac21346-8e0c-4494-8e7a-3eb92ff77902"
LEVER_API = (
    "https://api.lever.co/v0/postings/leverdemo/5ac21346-8e0c-4494-8e7a-3eb92ff77902?mode=json"
)
LEVER_JSON = {
    "id": "5ac21346-8e0c-4494-8e7a-3eb92ff77902",
    "text": "Backend Engineer",
    "categories": {"location": "Bengaluru", "team": "Engineering"},
    "descriptionPlain": "Build services.",
    "hostedUrl": LEVER_URL,
}

ASHBY_URL = "https://jobs.ashbyhq.com/acme/abc-123"
ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/acme"
ASHBY_JSON = {
    "apiVersion": "1",
    "jobs": [
        {
            "title": "Product Manager",
            "location": "Houston, TX",
            "descriptionPlain": "Own the roadmap.",
            "jobUrl": "https://jobs.ashbyhq.com/acme/abc-123",
        },
        {
            "title": "Designer",
            "location": "NYC",
            "descriptionPlain": "Design things.",
            "jobUrl": "https://jobs.ashbyhq.com/acme/xyz-999",
        },
    ],
}

SR_URL = "https://jobs.smartrecruiters.com/smartrecruiters/884352026-seo-manager"
SR_API = "https://api.smartrecruiters.com/v1/companies/smartrecruiters/postings/884352026"
SR_JSON = {
    "id": "884352026",
    "name": "SEO Manager",
    "company": {"identifier": "smartrecruiters", "name": "SmartRecruiters Inc"},
    "location": {"city": "San Francisco", "region": "CA", "country": "us", "remote": True},
    "jobAd": {
        "sections": {
            "companyDescription": {
                "title": "Company Description",
                "text": "We make hiring easy &amp; fast.",
            },
            "jobDescription": {"title": "Job Description", "text": "Own organic search."},
            "qualifications": {"title": "Qualifications", "text": "3-5 years of SEO."},
        }
    },
}

ATS_RESPONSES: dict[str, dict] = {
    GH_API: GH_JSON,
    LEVER_API: LEVER_JSON,
    ASHBY_API: ASHBY_JSON,
    SR_API: SR_JSON,
}


def ats_handler(request: httpx.Request) -> httpx.Response:
    data = ATS_RESPONSES.get(str(request.url))
    if data is None:
        return httpx.Response(404, json={"error": "not found"})
    return httpx.Response(200, json=data)


def ats_client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(ats_handler))
