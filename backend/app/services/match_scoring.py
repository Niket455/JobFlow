import re
from dataclasses import dataclass, field

SCORING_VERSION = "matching-v1"

WEIGHTS: dict[str, float] = {
    "skills": 35.0,
    "experience": 15.0,
    "location": 15.0,
    "salary": 15.0,
    "domain": 10.0,
    "education": 5.0,
    "notice": 5.0,
}

SENIORITY_BANDS: dict[str, tuple[float, float]] = {
    "intern": (0.0, 1.0),
    "entry": (0.0, 2.0),
    "junior": (0.0, 2.0),
    "mid": (2.0, 5.0),
    "middle": (2.0, 5.0),
    "senior": (5.0, 9.0),
    "lead": (8.0, 20.0),
    "staff": (8.0, 20.0),
    "principal": (8.0, 20.0),
    "manager": (6.0, 20.0),
}

_STOPWORDS = {"and", "the", "for", "with", "of", "a", "an", "to", "in", "on", "role", "job"}


@dataclass
class MatchInputs:
    job_title: str
    job_status: str
    job_location: str | None = None
    job_company: str | None = None
    skills_required: list[str] = field(default_factory=list)
    skills_preferred: list[str] = field(default_factory=list)
    seniority: str | None = None
    experience_years_required: float | None = None
    education_required: str | None = None
    salary: str | None = None
    notice_expectation: str | None = None
    keywords: list[str] = field(default_factory=list)
    user_skills: list[str] = field(default_factory=list)
    user_experience_years: float | None = None
    user_has_education: bool = False
    target_roles: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    min_salary: float | None = None
    notice_period_days: int | None = None
    excluded_companies: list[str] = field(default_factory=list)
    excluded_locations: list[str] = field(default_factory=list)


@dataclass
class ScoreResult:
    overall: float
    sub_scores: dict[str, float]
    recommendation: str
    excluded: bool
    reasons: list[str]
    evidence: dict[str, list[str]]


def score(inputs: MatchInputs) -> ScoreResult:
    """Deterministic, reproducible match score. Same inputs ⇒ identical output."""
    evidence: dict[str, list[str]] = {"matched": [], "partial": [], "missing": []}
    components: dict[str, tuple[float | None, str | None]] = {
        "skills": _skills_score(inputs, evidence),
        "experience": _experience_score(inputs),
        "location": _location_score(inputs),
        "salary": _salary_score(inputs),
        "domain": _domain_score(inputs),
        "education": _education_score(inputs),
        "notice": _notice_score(inputs),
    }

    sub_scores = {
        name: round(value, 1) for name, (value, _) in components.items() if value is not None
    }
    total_weight = sum(WEIGHTS[name] for name in sub_scores)
    overall = (
        round(sum(sub_scores[name] * WEIGHTS[name] for name in sub_scores) / total_weight, 1)
        if total_weight > 0
        else 0.0
    )

    reasons = [
        reason
        for name, (value, reason) in components.items()
        if value is not None and reason is not None
    ]
    excluded = _is_excluded(inputs)
    if excluded:
        recommendation = "not_recommended"
        reasons.insert(0, "Excluded by your deal-breakers")
    elif inputs.job_status != "Active":
        recommendation = "not_recommended"
        reasons.insert(0, f"Job is {inputs.job_status}, not currently active")
    else:
        recommendation = _tier(overall)

    return ScoreResult(overall, sub_scores, recommendation, excluded, reasons, evidence)


def _skills_score(
    inputs: MatchInputs, evidence: dict[str, list[str]]
) -> tuple[float | None, str | None]:
    required = _dedupe(inputs.skills_required)
    if not required:
        return None, None
    preferred = _dedupe(inputs.skills_preferred)
    user = {_norm(skill) for skill in inputs.user_skills if skill}

    matched = [skill for skill in required if _norm(skill) in user]
    missing = [skill for skill in required if _norm(skill) not in user]
    partial = [skill for skill in preferred if _norm(skill) in user]
    evidence["matched"] = matched
    evidence["partial"] = partial
    evidence["missing"] = missing

    required_ratio = len(matched) / len(required)
    preferred_ratio = len(partial) / len(preferred) if preferred else required_ratio
    value = (0.8 * required_ratio + 0.2 * preferred_ratio) * 10
    reason = f"Skills {value:.1f}/10: {len(matched)}/{len(required)} required present"
    if missing:
        reason += f"; missing {', '.join(missing[:5])}"
    return value, reason


def _experience_score(inputs: MatchInputs) -> tuple[float | None, str | None]:
    years = inputs.user_experience_years
    if years is None:
        return None, None
    if inputs.experience_years_required is not None:
        required = inputs.experience_years_required
        value = 10.0 if years >= required else max(0.0, 10.0 - (required - years) * 2.0)
        return value, f"Experience {value:.1f}/10: {years:g}y vs {required:g}y required"
    band = SENIORITY_BANDS.get(_norm(inputs.seniority or ""))
    if band is None:
        return None, None
    low, high = band
    if low <= years <= high:
        value = 10.0
    elif years < low:
        value = max(0.0, 10.0 - (low - years) * 3.0)
    else:
        value = 8.0
    return value, f"Experience {value:.1f}/10: {years:g}y vs {inputs.seniority} band"


def _education_score(inputs: MatchInputs) -> tuple[float | None, str | None]:
    if not inputs.education_required:
        return None, None
    if inputs.user_has_education:
        return 10.0, "Education: meets the stated requirement"
    return 4.0, f"Education: posting asks for {inputs.education_required}"


def _location_score(inputs: MatchInputs) -> tuple[float | None, str | None]:
    job_location = _norm(inputs.job_location)
    if not job_location:
        return None, None
    if "remote" in job_location or "anywhere" in job_location:
        return 10.0, "Location: remote"
    preferred = [_norm(loc) for loc in inputs.preferred_locations if loc]
    if not preferred:
        return None, None
    if any(p == job_location or p in job_location or job_location in p for p in preferred):
        return 10.0, f"Location {inputs.job_location} matches your preferences"
    return 3.0, f"Location {inputs.job_location} is outside your preferred locations"


def _salary_score(inputs: MatchInputs) -> tuple[float | None, str | None]:
    target = inputs.min_salary
    if not target or target <= 0 or not inputs.salary:
        return None, None
    annual = _parse_salary_annual(inputs.salary)
    if annual is None:
        return None, None
    value = 10.0 if annual >= target else max(0.0, 10.0 * (annual / target))
    return value, f"Salary {inputs.salary!r} vs your minimum of {target:,.0f}"


def _domain_score(inputs: MatchInputs) -> tuple[float | None, str | None]:
    desired = " ".join([*inputs.target_roles, *inputs.industries])
    desired_tokens = _tokens(desired)
    if not desired_tokens:
        return None, None
    job_tokens = _tokens(" ".join([inputs.job_title, *inputs.keywords]))
    overlap = desired_tokens & job_tokens
    value = min(10.0, len(overlap) / len(desired_tokens) * 10)
    return value, f"Role/domain overlap: {len(overlap)}/{len(desired_tokens)} terms"


def _notice_score(inputs: MatchInputs) -> tuple[float | None, str | None]:
    if inputs.notice_period_days is None or not inputs.notice_expectation:
        return None, None
    expected = _parse_days(inputs.notice_expectation)
    if expected is None:
        return None, None
    if inputs.notice_period_days <= expected:
        return 10.0, f"Notice {inputs.notice_period_days}d is within the expected {expected}d"
    excess = inputs.notice_period_days - expected
    value = max(0.0, 10.0 - excess * 0.5)
    return value, f"Notice {inputs.notice_period_days}d exceeds the expected {expected}d"


def _is_excluded(inputs: MatchInputs) -> bool:
    company = _norm(inputs.job_company)
    if company and _any_contains(inputs.excluded_companies, company):
        return True
    location = _norm(inputs.job_location)
    return bool(location and _any_contains(inputs.excluded_locations, location))


def _any_contains(candidates: list[str], value: str) -> bool:
    for candidate in candidates:
        normalized = _norm(candidate)
        if normalized and (normalized == value or normalized in value or value in normalized):
            return True
    return False


def _tier(overall: float) -> str:
    if overall >= 8.0:
        return "strong"
    if overall >= 6.0:
        return "good"
    if overall >= 4.0:
        return "partial"
    return "weak"


def _parse_salary_annual(text: str) -> float | None:
    numbers = [float(match.replace(",", "")) for match in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]
    if not numbers:
        return None
    value = max(numbers)
    return value * 100_000 if value <= 100 else value


def _parse_days(text: str) -> int | None:
    lowered = text.lower()
    if "immediate" in lowered:
        return 0
    match = re.search(r"\d+", lowered)
    if match is None:
        return None
    days = int(match.group())
    if "week" in lowered:
        return days * 7
    if "month" in lowered:
        return days * 30
    return days


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9+#]+", text.lower())
        if len(token) >= 3 and token not in _STOPWORDS
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = _norm(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result
