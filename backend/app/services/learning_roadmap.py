from dataclasses import dataclass


@dataclass(frozen=True)
class RoadmapItem:
    skill: str
    priority: int
    demand_pct: float
    jobs: int
    rationale: str


def build_roadmap(missing: list[tuple[str, int, float]]) -> list[RoadmapItem]:
    """Turn the skill gap's missing skills into a prioritized roadmap.

    `missing` items are `(skill, jobs, demand_pct)`.
    """
    ordered = sorted(missing, key=lambda entry: (-entry[1], entry[0].lower()))
    return [
        RoadmapItem(
            skill=skill,
            priority=index + 1,
            demand_pct=demand_pct,
            jobs=jobs,
            rationale=f"Required by {jobs} of your tracked jobs ({demand_pct}%).",
        )
        for index, (skill, jobs, demand_pct) in enumerate(ordered)
    ]
