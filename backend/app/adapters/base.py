from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)


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
