import re
from dataclasses import dataclass

_METRIC = re.compile(r"\d|%|\$|€|£")
_STAR_TERMS: dict[str, tuple[str, ...]] = {
    "situation": ("situation", "context", "background", "at the time", "challenge"),
    "task": ("task", "goal", "objective", "responsible for", "needed to", "asked to"),
    "action": (
        "action",
        "i built",
        "i led",
        "i implemented",
        "i designed",
        "i created",
        "i drove",
        "i introduced",
        "i wrote",
    ),
    "result": (
        "result",
        "outcome",
        "impact",
        "improved",
        "reduced",
        "increased",
        "saved",
        "grew",
        "delivered",
    ),
}


@dataclass(frozen=True)
class AnswerSignals:
    word_count: int
    has_metric: bool
    star_coverage: dict[str, bool]


def analyze_answer(text: str) -> AnswerSignals:
    """Deterministic, reproducible signals about a practice answer (no model, no clock)."""
    lowered = text.lower()
    coverage = {part: any(term in lowered for term in terms) for part, terms in _STAR_TERMS.items()}
    return AnswerSignals(
        word_count=len(text.split()),
        has_metric=bool(_METRIC.search(text)),
        star_coverage=coverage,
    )
