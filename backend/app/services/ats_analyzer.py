import re

from app.core.media_types import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from app.schemas.ats import AtsCheck, AtsKeyword, AtsParseTest, AtsReport
from app.schemas.job_analysis import JobAnalysisData
from app.schemas.profile import ProfileData
from app.services.resume_parser import extract_text
from app.services.resume_renderer import render_docx, render_pdf
from app.services.tailor_grounding import normalize

MAX_PARSE_PDF = 20
MAX_PARSE_DOCX = 15
MAX_CONTACT = 10
MAX_SECTIONS = 15
MAX_KEYWORDS = 25
MAX_IMPACT = 10
MAX_LENGTH = 5

MIN_WORDS = 100
MAX_WORDS = 1500

_SECTION_HEADINGS: tuple[tuple[str, str], ...] = (
    ("summary", "Summary"),
    ("work_history", "Experience"),
    ("education", "Education"),
    ("skills", "Skills"),
    ("projects", "Projects"),
    ("certifications", "Certifications"),
    ("achievements", "Achievements"),
)


def analyze_ats(profile: ProfileData, job: JobAnalysisData | None = None) -> AtsReport:
    """Deterministic ATS report: render → re-extract parse test plus structure/keyword checks."""
    pdf_fields = _parse_fields(profile, _extract(profile, "pdf"))
    docx_text = _extract(profile, "docx")
    docx_fields = _parse_fields(profile, docx_text)

    checks: list[AtsCheck] = [
        _field_check("parse_pdf", "PDF parse test", MAX_PARSE_PDF, pdf_fields),
        _field_check("parse_docx", "DOCX parse test", MAX_PARSE_DOCX, docx_fields),
        _contact_check(profile),
        _sections_check(profile, docx_text),
    ]

    keywords: AtsKeyword | None = None
    if job is not None:
        keywords = _keyword_coverage(docx_text, job)
        if keywords is not None:
            checks.append(_keyword_check(keywords))
    if profile.work_history:
        checks.append(_impact_check(profile))
    checks.append(_length_check(docx_text))

    total_max = sum(check.max_score for check in checks)
    score = round(100 * sum(check.score for check in checks) / total_max) if total_max else 0
    return AtsReport(
        score=score,
        grade=_grade(score),
        parse_test=AtsParseTest(
            passed=all(pdf_fields.values()) and all(docx_fields.values()),
            extracted=docx_fields,
            missing=[name for name, ok in docx_fields.items() if not ok],
        ),
        checks=checks,
        keywords=keywords,
        recommendations=_recommendations(checks, keywords),
    )


def _extract(profile: ProfileData, fmt: str) -> str:
    if fmt == "pdf":
        return extract_text(PDF_CONTENT_TYPE, render_pdf(profile))
    return extract_text(DOCX_CONTENT_TYPE, render_docx(profile))


def _parse_fields(profile: ProfileData, text: str) -> dict[str, bool]:
    norm = normalize(text)
    fields: dict[str, bool] = {}
    if profile.full_name:
        fields["name"] = normalize(profile.full_name) in norm
    if profile.email:
        fields["email"] = normalize(str(profile.email)) in norm
    if profile.phone:
        fields["phone"] = normalize(profile.phone) in norm
    if profile.skills:
        fields["skills"] = all(normalize(skill) in norm for skill in profile.skills)
    return fields or {"content": bool(norm)}


def _field_check(check_id: str, label: str, max_score: int, fields: dict[str, bool]) -> AtsCheck:
    total = len(fields)
    recovered = sum(1 for ok in fields.values() if ok)
    missing = [name for name, ok in fields.items() if not ok]
    return AtsCheck(
        id=check_id,
        label=label,
        score=round(max_score * recovered / total) if total else max_score,
        max_score=max_score,
        passed=not missing,
        detail="All fields recovered." if not missing else f"Missing: {', '.join(missing)}",
    )


def _contact_check(profile: ProfileData) -> AtsCheck:
    present = {
        "email": bool(profile.email),
        "phone": bool(profile.phone),
        "location": bool(profile.location),
    }
    missing = [name for name, ok in present.items() if not ok]
    return AtsCheck(
        id="contact",
        label="Contact details",
        score=round(MAX_CONTACT * (len(present) - len(missing)) / len(present)),
        max_score=MAX_CONTACT,
        passed=not missing,
        detail="Contact block complete." if not missing else f"Add: {', '.join(missing)}",
    )


def _sections_check(profile: ProfileData, text: str) -> AtsCheck:
    expected = [heading for attr, heading in _SECTION_HEADINGS if getattr(profile, attr)]
    norm = normalize(text)
    missing = [heading for heading in expected if normalize(heading) not in norm]
    score = round(MAX_SECTIONS * (len(expected) - len(missing)) / len(expected)) if expected else 0
    if not expected:
        detail = "No standard sections found."
    elif not missing:
        detail = "All expected sections detected."
    else:
        detail = f"Missing headings: {', '.join(missing)}"
    return AtsCheck(
        id="sections",
        label="Standard sections",
        score=score,
        max_score=MAX_SECTIONS,
        passed=bool(expected) and not missing,
        detail=detail,
    )


def _keyword_coverage(text: str, job: JobAnalysisData) -> AtsKeyword | None:
    terms = _dedupe_terms([*job.skills_required, *job.skills_preferred, *job.keywords])
    if not terms:
        return None
    norm = normalize(text)
    matched = [term for term in terms if normalize(term) in norm]
    missing = [term for term in terms if normalize(term) not in norm]
    return AtsKeyword(
        matched=matched, missing=missing, coverage=round(len(matched) / len(terms), 4)
    )


def _keyword_check(keywords: AtsKeyword) -> AtsCheck:
    total = len(keywords.matched) + len(keywords.missing)
    return AtsCheck(
        id="keywords",
        label="Job keyword coverage",
        score=round(MAX_KEYWORDS * keywords.coverage),
        max_score=MAX_KEYWORDS,
        passed=not keywords.missing,
        detail=f"{len(keywords.matched)}/{total} job terms present.",
    )


def _impact_check(profile: ProfileData) -> AtsCheck:
    total = len(profile.work_history)
    with_metrics = sum(
        1
        for item in profile.work_history
        if item.description and re.search(r"\d", item.description)
    )
    return AtsCheck(
        id="impact",
        label="Quantified impact",
        score=round(MAX_IMPACT * with_metrics / total) if total else MAX_IMPACT,
        max_score=MAX_IMPACT,
        passed=with_metrics > 0,
        detail=f"{with_metrics}/{total} roles mention numbers or metrics.",
    )


def _length_check(text: str) -> AtsCheck:
    words = len(text.split())
    passed = MIN_WORDS <= words <= MAX_WORDS
    if words < MIN_WORDS:
        score = round(MAX_LENGTH * words / MIN_WORDS)
    else:
        score = MAX_LENGTH if passed else MAX_LENGTH // 2
    return AtsCheck(
        id="length",
        label="Resume length",
        score=score,
        max_score=MAX_LENGTH,
        passed=passed,
        detail=f"{words} words (target {MIN_WORDS}–{MAX_WORDS}).",
    )


def _recommendations(checks: list[AtsCheck], keywords: AtsKeyword | None) -> list[str]:
    recommendations = [f"{check.label}: {check.detail}" for check in checks if not check.passed]
    if keywords is not None and keywords.missing:
        recommendations.append(
            "Consider adding these job terms you genuinely have: "
            + ", ".join(keywords.missing[:10])
        )
    return recommendations


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        key = normalize(term)
        if key and key not in seen:
            seen.add(key)
            result.append(term)
    return result


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
