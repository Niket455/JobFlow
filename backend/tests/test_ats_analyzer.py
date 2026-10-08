from app.schemas.job_analysis import JobAnalysisData
from app.schemas.profile import EducationItem, ProfileData, WorkItem
from app.services.ats_analyzer import analyze_ats


def _profile() -> ProfileData:
    return ProfileData(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="+91 9000000000",
        location="Bengaluru",
        summary="Data engineer with 6 years building pipelines.",
        skills=["Python", "SQL", "PySpark"],
        work_history=[
            WorkItem(
                company="Acme",
                title="Data Engineer",
                description="Cut pipeline latency by 40% and saved $10k.",
            )
        ],
        education=[EducationItem(institution="IIT", degree="BTech")],
    )


def _job() -> JobAnalysisData:
    return JobAnalysisData(skills_required=["Python", "SQL", "Go"], keywords=["Airflow"])


def test_report_structure_and_parse_test() -> None:
    report = analyze_ats(_profile(), _job())

    assert 0 <= report.score <= 100
    assert report.grade in {"A", "B", "C", "D", "F"}
    assert report.parse_test.passed is True
    ids = {check.id for check in report.checks}
    assert {"parse_pdf", "parse_docx", "contact", "sections", "keywords", "impact"} <= ids


def test_keyword_coverage_and_recommendation() -> None:
    report = analyze_ats(_profile(), _job())

    assert report.keywords is not None
    assert "Python" in report.keywords.matched
    assert "SQL" in report.keywords.matched
    assert "Go" in report.keywords.missing
    assert report.keywords.coverage == 0.5

    keyword_check = next(check for check in report.checks if check.id == "keywords")
    assert keyword_check.passed is False
    assert report.recommendations


def test_no_job_omits_keywords() -> None:
    report = analyze_ats(_profile())

    assert report.keywords is None
    assert "keywords" not in {check.id for check in report.checks}
    assert "impact" in {check.id for check in report.checks}


def test_contact_gap_fails_check() -> None:
    report = analyze_ats(ProfileData(full_name="X", skills=["Python"]))

    contact = next(check for check in report.checks if check.id == "contact")
    assert contact.passed is False
    assert contact.score < contact.max_score
