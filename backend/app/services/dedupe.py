import hashlib
import re

_COMPANY_SUFFIXES = {
    "co",
    "corp",
    "corporation",
    "gmbh",
    "inc",
    "limited",
    "llc",
    "ltd",
    "plc",
    "private",
    "pvt",
}


def normalized_company_name(name: str | None) -> str:
    if not name:
        return ""
    lowered = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    tokens = [token for token in lowered.split() if token and token not in _COMPANY_SUFFIXES]
    return " ".join(tokens)


def _normalize_field(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def content_hash(title: str, company: str | None, location: str | None) -> str:
    key = "|".join(
        [_normalize_field(title), normalized_company_name(company), _normalize_field(location)]
    )
    return hashlib.sha256(key.encode()).hexdigest()
