from app.services.skill_gap import analyze_skill_gap


def test_demand_counts_and_split() -> None:
    gap = analyze_skill_gap(
        ["Python", "SQL"],
        [["Python", "SQL", "Go"], ["Python", "Go"], ["Rust"]],
    )

    assert gap.total_jobs == 3
    have = {item.skill: item for item in gap.have}
    assert have["Python"].jobs == 2
    assert have["SQL"].jobs == 1
    missing = {item.skill: item for item in gap.missing}
    assert missing["Go"].jobs == 2
    assert missing["Go"].demand_pct == 66.7
    assert missing["Rust"].jobs == 1
    assert missing["Rust"].demand_pct == 33.3


def test_normalization_and_within_job_dedupe() -> None:
    gap = analyze_skill_gap(["python"], [["Python", " python "], ["PYTHON"]])

    assert gap.total_jobs == 2
    assert len(gap.have) == 1
    assert gap.have[0].jobs == 2  # counted once per job, across both jobs
    assert gap.missing == []


def test_empty_jobs() -> None:
    gap = analyze_skill_gap(["Python"], [])

    assert gap.total_jobs == 0
    assert gap.have == []
    assert gap.missing == []


def test_ranking_prefers_higher_job_count() -> None:
    gap = analyze_skill_gap([], [["Go"], ["Go"], ["Rust", "Go"], ["Rust"]])

    assert [item.skill for item in gap.missing] == ["Go", "Rust"]
