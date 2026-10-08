from app.adapters.base import Adapter, Fetcher, FetchError, FetchResult


class DispatchFetcher:
    """Route a URL to the first adapter that recognises it; else the generic HTML fallback.

    If a recognized adapter fails (transport error, unexpected payload), we fall back to the
    generic fetcher so ingestion never regresses for a URL that also renders as HTML.
    """

    def __init__(self, adapters: list[Adapter], fallback: Fetcher) -> None:
        self._adapters = adapters
        self._fallback = fallback

    def fetch(self, url: str) -> FetchResult:
        for adapter in self._adapters:
            if adapter.matches(url):
                try:
                    return adapter.fetch(url)
                except FetchError:
                    break
        return self._fallback.fetch(url)
