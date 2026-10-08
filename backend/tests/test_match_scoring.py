from app.services.match_scoring import SCORING_VERSION, MatchInputs, score


def test_partitions_skills_into_matched_partial_missing() -> None:
    result = score(
        MatchInputs(
            job_title="Senior Data Engineer",
            job_status="Active",
            skills_required=["Python", "SQL", "Spark"],
            skills_preferred=["AWS"],
            user_skills=["Python", "SQL", "AWS"],
        )
    )
    assert result.evidence["matched"] == ["Python", "SQL"]
    assert result.evidence["missing"] == ["Spark"]
    assert result.evidence["partial"] == ["AWS"]
    assert result.sub_scores["skills"] == 7.3


def test_unknown_signals_are_dropped() -> None:
    result = score(MatchInputs(job_title="Anything", job_status="Active"))
    assert result.sub_scores == {}
    assert result.overall == 0.0
    assert result.recommendation == "weak"


def test_full_match_scores_ten_and_strong() -> None:
    result = score(
        MatchInputs(
            job_title="Data Engineer",
            job_status="Active",
            job_location="Bengaluru",
            skills_required=["Python", "SQL"],
            user_skills=["Python", "SQL"],
            seniority="senior",
            user_experience_years=6,
            user_has_education=True,
            education_required="Bachelor's degree",
            preferred_locations=["Bengaluru"],
            salary="20 LPA",
            min_salary=1_500_000,
            target_roles=["Data Engineer"],
            notice_expectation="30 days",
            notice_period_days=30,
        )
    )
    assert result.overall == 10.0
    assert result.recommendation == "strong"
    assert result.excluded is False


def test_salary_below_target_scores_proportionally() -> None:
    result = score(
        MatchInputs(job_title="X", job_status="Active", salary="10 LPA", min_salary=2_000_000)
    )
    assert result.sub_scores["salary"] == 5.0


def test_deal_breaker_excludes_job() -> None:
    result = score(
        MatchInputs(
            job_title="X",
            job_status="Active",
            job_company="Acme Inc",
            excluded_companies=["Acme"],
        )
    )
    assert result.excluded is True
    assert result.recommendation == "not_recommended"
    assert result.reasons[0] == "Excluded by your deal-breakers"


def test_non_active_job_is_never_recommended() -> None:
    result = score(
        MatchInputs(
            job_title="X",
            job_status="Expired",
            skills_required=["Python"],
            user_skills=["Python"],
        )
    )
    assert result.sub_scores["skills"] == 10.0
    assert result.recommendation == "not_recommended"


def test_scoring_is_deterministic() -> None:
    inputs = MatchInputs(
        job_title="Data Engineer",
        job_status="Active",
        skills_required=["Python", "SQL"],
        user_skills=["Python"],
    )
    assert score(inputs) == score(inputs)
    assert score(inputs).sub_scores == {"skills": 5.0}
    assert SCORING_VERSION == "matching-v1"
