from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)
    adapter: str = "user_url"


class FetchError(Exception):
    def __init__(self, url: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(f"{message}: {url}")
        self.url = url
        self.status_code = status_code


class RobotsDisallowedError(Exception):
    def __init__(self, url: str) -> None:
        super().__init__(f"robots.txt disallows fetching {url}")
        self.url = url


class Fetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


class Adapter(Protocol):
    """A source-specific fetcher that recognizes URLs it owns and emits provenance.

    ATS adapters (Greenhouse/Lever/Ashby) also feed an adapter label into FetchResult so the
    ingestion pipeline can record where a job came from.
    """

    name: str

    def matches(self, url: str) -> bool: ...

    def fetch(self, url: str) -> FetchResult: ...
