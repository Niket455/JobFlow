from dataclasses import dataclass, field

from app.services.application_status import STAGE_BY_EVENT

_STAGE_RANK = {"Saved": 0, "Applied": 1, "Interview": 2, "Offer": 3}
_STAGE_LABEL = {rank: label for label, rank in _STAGE_RANK.items()}
_FUNNEL_KEYS = ("saved", "applied", "interview", "offer", "rejected", "withdrawn")


@dataclass(frozen=True)
class ApplicationRow:
    status: str
    event_types: list[str]
    source: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    resume_version_id: str | None = None
    month: str | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RateMetric:
    numerator: int
    denominator: int
    value: float | None
    sufficient_sample: bool


@dataclass(frozen=True)
class Bucket:
    key: str
    total: int
    rejected: int
    rate: float | None
    sufficient_sample: bool


@dataclass(frozen=True)
class RejectionReport:
    total_rejected: int
    buckets: list[Bucket]
    stages: dict[str, int]
    reasons: list[str]


def stage_rank(event_types: list[str]) -> int:
    """Max funnel-progress rank reached (Saved=0 … Offer=3). Outcomes don't count as progress."""
    best = 0
    for event_type in event_types:
        stage = STAGE_BY_EVENT.get(event_type.strip().lower())
        if stage in _STAGE_RANK:
            best = max(best, _STAGE_RANK[stage])
    return best


def funnel(rows: list[ApplicationRow]) -> dict[str, int]:
    counts = dict.fromkeys(_FUNNEL_KEYS, 0)
    for row in rows:
        rank = stage_rank(row.event_types)
        counts["saved"] += 1 if rank == 0 else 0
        counts["applied"] += 1 if rank >= 1 else 0
        counts["interview"] += 1 if rank >= 2 else 0
        counts["offer"] += 1 if rank >= 3 else 0
        counts["rejected"] += 1 if row.status == "Rejected" else 0
        counts["withdrawn"] += 1 if row.status == "Withdrawn" else 0
    return counts


def rates(rows: list[ApplicationRow], min_sample: int) -> dict[str, RateMetric]:
    applied = [row for row in rows if stage_rank(row.event_types) >= 1]
    applied_count = len(applied)
    interview = sum(1 for row in applied if stage_rank(row.event_types) >= 2)
    offer = sum(1 for row in applied if stage_rank(row.event_types) >= 3)
    responded = sum(
        1 for row in applied if row.status == "Rejected" or stage_rank(row.event_types) >= 2
    )
    return {
        "response": _rate(responded, applied_count, min_sample),
        "interview": _rate(interview, applied_count, min_sample),
        "offer": _rate(offer, applied_count, min_sample),
        "offer_from_interview": _rate(offer, interview, min_sample),
    }


def group_by(rows: list[ApplicationRow], by: str) -> dict[str, list[ApplicationRow]]:
    grouped: dict[str, list[ApplicationRow]] = {}
    for row in rows:
        grouped.setdefault(bucket_key(row, by), []).append(row)
    return grouped


def rejections(rows: list[ApplicationRow], by: str, min_sample: int) -> RejectionReport:
    rejected_rows = [row for row in rows if row.status == "Rejected"]
    buckets = [_bucket(key, group, min_sample) for key, group in sorted(group_by(rows, by).items())]

    stages: dict[str, int] = {}
    for row in rejected_rows:
        label = _STAGE_LABEL.get(stage_rank(row.event_types), "Saved")
        stages[label] = stages.get(label, 0) + 1

    reasons = sorted({reason for row in rejected_rows for reason in row.reasons if reason})
    return RejectionReport(len(rejected_rows), buckets, stages, reasons)


def _rate(numerator: int, denominator: int, min_sample: int) -> RateMetric:
    value = round(numerator / denominator, 4) if denominator else None
    return RateMetric(numerator, denominator, value, denominator >= min_sample)


def _bucket(key: str, group: list[ApplicationRow], min_sample: int) -> Bucket:
    total = len(group)
    rejected = sum(1 for row in group if row.status == "Rejected")
    sufficient = total >= min_sample
    rate = round(rejected / total, 4) if sufficient else None
    return Bucket(key, total, rejected, rate, sufficient)


def bucket_key(row: ApplicationRow, by: str) -> str:
    value: str | None
    if by == "resume_version":
        value = row.resume_version_id
    else:
        value = {
            "source": row.source,
            "company": row.company,
            "role": row.role,
            "location": row.location,
            "month": row.month,
        }.get(by)
    return value or "unknown"
