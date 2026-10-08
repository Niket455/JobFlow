from typing import Any

import httpx

from app.adapters.base import FetchError


def get_json(client: httpx.Client, url: str) -> Any:
    """GET a JSON document, mapping transport/HTTP/parse failures to FetchError."""
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise FetchError(url, str(exc)) from exc
    if response.status_code >= 400:
        raise FetchError(url, f"HTTP {response.status_code}", status_code=response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        raise FetchError(url, "response was not JSON") from exc
