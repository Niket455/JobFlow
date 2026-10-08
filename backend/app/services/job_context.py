import json

from app.models.job import Job
from app.models.job_analysis import JobAnalysis


def job_text(job: Job, analysis: JobAnalysis | None) -> str:
    """Render a job (plus its LLM analysis, when present) as prompt input."""
    parts = [f"Title: {job.title}"]
    if job.location:
        parts.append(f"Location: {job.location}")
    if analysis is not None:
        parts.append(f"Extracted: {json.dumps(analysis.data)}")
    if job.description:
        parts.append(job.description)
    return "\n".join(parts)
