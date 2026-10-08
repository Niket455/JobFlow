from app.services.application_analytics import (
    ApplicationRow,
    funnel,
    rates,
    rejections,
    stage_rank,
)


def _row(status: str, event_types: list[str], **kwargs: object) -> ApplicationRow:
    return ApplicationRow(status=status, event_types=event_types, **kwargs)


def test_stage_rank_ignores_outcomes() -> None:
    assert stage_rank(["saved"]) == 0
    assert stage_rank(["saved", "applied"]) == 1
    assert stage_rank(["applied", "interview"]) == 2
    assert stage_rank(["offer"]) == 3
    assert stage_rank(["rejected"]) == 0


def test_funnel_counts_reached_stages() -> None:
    rows = [
        _row("Saved", []),
        _row("Applied", ["applied"]),
        _row("Interview", ["applied", "interview"]),
        _row("Offer", ["applied", "interview", "offer"]),
        _row("Rejected", ["applied", "interview", "rejected"]),
        _row("Withdrawn", ["applied", "withdrawn"]),
    ]
    counts = funnel(rows)
    assert counts["saved"] == 1
    assert counts["applied"] == 5
    assert counts["interview"] == 3
    assert counts["offer"] == 1
    assert counts["rejected"] == 1
    assert counts["withdrawn"] == 1


def test_rates_and_min_sample_suppression() -> None:
    rows = [
        _row("Interview", ["applied", "interview"]),
        _row("Rejected", ["applied", "rejected"]),
        _row("Applied", ["applied"]),
    ]
    enough = rates(rows, min_sample=2)
    assert enough["interview"].numerator == 1
    assert enough["interview"].denominator == 3
    assert enough["interview"].value == round(1 / 3, 4)
    assert enough["interview"].sufficient_sample is True

    strict = rates(rows, min_sample=5)
    assert strict["interview"].sufficient_sample is False
    assert strict["interview"].value is not None  # overall rates always carry a value


def test_rejection_buckets_and_suppression() -> None:
    rows = [
        _row("Rejected", ["applied", "rejected"], source="linkedin", reasons=["no response"]),
        _row("Rejected", ["applied", "rejected"], source="linkedin", reasons=["no response"]),
        _row("Applied", ["applied"], source="referral"),
    ]
    report = rejections(rows, by="source", min_sample=2)
    by_key = {bucket.key: bucket for bucket in report.buckets}

    assert report.total_rejected == 2
    assert by_key["linkedin"].total == 2
    assert by_key["linkedin"].rejected == 2
    assert by_key["linkedin"].rate == 1.0
    assert by_key["linkedin"].sufficient_sample is True

    assert by_key["referral"].total == 1
    assert by_key["referral"].rate is None
    assert by_key["referral"].sufficient_sample is False

    assert report.stages == {"Applied": 2}
    assert report.reasons == ["no response"]
