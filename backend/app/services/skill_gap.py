from dataclasses import dataclass

from app.services.tailor_grounding import normalize

_REQUIRED = "skills_required"
_PREFERRED = "skills_preferred"
_KEYWORDS = "keywords"


@dataclass(frozen=True)
class SkillDemand:
    skill: str
    jobs: int
    demand_pct: float


@dataclass(frozen=True)
class SkillGap:
    total_jobs: int
    have: list[SkillDemand]
    missing: list[SkillDemand]


@dataclass
class _Count:
    label: str
    jobs: int


def job_terms(data: dict[str, object]) -> list[str]:
    """The demand-bearing terms of one job analysis (required + preferred skills + keywords)."""
    terms: list[str] = []
    for key in (_REQUIRED, _PREFERRED, _KEYWORDS):
        values = data.get(key)
        if isinstance(values, list):
            terms.extend(str(value) for value in values if value)
    return terms


def analyze_skill_gap(have: list[str], jobs: list[list[str]]) -> SkillGap:
    """Fold per-job terms into per-skill demand; split into skills the user has vs is missing.

    A `missing` skill's `jobs` count is its marginal-coverage gain: how many tracked postings it
    would help cover.
    """
    total = len(jobs)
    counts: dict[str, _Count] = {}
    for terms in jobs:
        seen: set[str] = set()
        for term in terms:
            key = normalize(term)
            if not key or key in seen:
                continue
            seen.add(key)
            entry = counts.get(key)
            if entry is None:
                counts[key] = _Count(label=term, jobs=1)
            else:
                entry.jobs += 1

    have_keys = {normalize(skill) for skill in have if normalize(skill)}
    have_out: list[SkillDemand] = []
    missing_out: list[SkillDemand] = []
    for key, entry in counts.items():
        demand = SkillDemand(
            skill=entry.label,
            jobs=entry.jobs,
            demand_pct=round(100 * entry.jobs / total, 1) if total else 0.0,
        )
        (have_out if key in have_keys else missing_out).append(demand)

    return SkillGap(
        total_jobs=total,
        have=sorted(have_out, key=_order_key),
        missing=sorted(missing_out, key=_order_key),
    )


def _order_key(item: SkillDemand) -> tuple[int, str]:
    return (-item.jobs, item.skill.lower())
