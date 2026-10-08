import re
from typing import Any


def as_text(value: Any) -> str | None:
    """Collapse a scalar to non-empty text (whitespace-normalized)."""
    if isinstance(value, str):
        collapsed = re.sub(r"\s+", " ", value).strip()
        return collapsed or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def humanize_token(token: str) -> str:
    """Turn an ATS board/org slug into a plausible company display name."""
    return re.sub(r"[-_]+", " ", token).strip().title()


def named_value(value: Any) -> str | None:
    """Read a `{"name": ...}` object (or bare scalar)."""
    if isinstance(value, dict):
        return as_text(value.get("name"))
    return as_text(value)


def postal_location(value: Any) -> str | None:
    """Join an Ashby `address.postalAddress` object into a single location string."""
    if isinstance(value, dict):
        postal = value.get("postalAddress")
        if isinstance(postal, dict):
            parts = [
                as_text(postal.get(key))
                for key in ("addressLocality", "addressRegion", "addressCountry")
            ]
            return ", ".join(part for part in parts if part) or None
    return None
