import re
from dataclasses import dataclass
from typing import Any

MIN_SPAN_LENGTH = 4


@dataclass(frozen=True)
class AppliedChange:
    path: str
    new_text: str


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, and collapse whitespace — the shared match normalizer."""
    lowered = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", lowered).strip()


def is_grounded(source_span: str | None, corpus: str) -> bool:
    """True when the cited span appears (normalised) in the grounding corpus."""
    if not source_span:
        return False
    span = normalize(source_span)
    if len(span) < MIN_SPAN_LENGTH:
        return False
    return span in normalize(corpus)


def _resolve(profile: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = profile
    for part in path.split("."):
        if isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                return False, None
            current = current[int(part)]
        elif isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        else:
            return False, None
    return True, current


def path_exists(profile: dict[str, Any], path: str) -> bool:
    found, _ = _resolve(profile, path)
    return found


def get_text(profile: dict[str, Any], path: str) -> str | None:
    found, value = _resolve(profile, path)
    return value if found and isinstance(value, str) else None


def apply_changes(profile: dict[str, Any], changes: list[AppliedChange]) -> dict[str, Any]:
    """Return a deep copy of `profile` with each change applied; unknown paths are skipped."""
    import copy

    result = copy.deepcopy(profile)
    for change in changes:
        _set_text(result, change.path, change.new_text)
    return result


def _set_text(profile: dict[str, Any], path: str, value: str) -> bool:
    parts = path.split(".")
    current: Any = profile
    for part in parts[:-1]:
        if isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                return False
            current = current[int(part)]
        elif isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        else:
            return False
    last = parts[-1]
    if isinstance(current, list):
        if not last.isdigit() or int(last) >= len(current):
            return False
        current[int(last)] = value
        return True
    if isinstance(current, dict):
        if last not in current:
            return False
        current[last] = value
        return True
    return False
