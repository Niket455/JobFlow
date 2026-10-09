from app.services.learning_roadmap import build_roadmap


def test_roadmap_ranks_by_jobs_then_skill() -> None:
    items = build_roadmap([("Rust", 1, 25.0), ("Go", 3, 75.0), ("Airflow", 3, 75.0)])

    assert [item.skill for item in items] == ["Airflow", "Go", "Rust"]
    assert [item.priority for item in items] == [1, 2, 3]
    assert items[0].jobs == 3
    assert items[0].demand_pct == 75.0
    assert "3 of your tracked jobs" in items[0].rationale


def test_empty_roadmap() -> None:
    assert build_roadmap([]) == []
