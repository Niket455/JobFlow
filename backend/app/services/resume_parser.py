import io

import pdfplumber
from docx import Document

from app.core.media_types import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from app.core.prompts import load_prompt
from app.gateway.base import LLMMessage
from app.gateway.gateway import LLMGateway
from app.schemas.profile import ProfileData
from app.schemas.resume import ResumeExtraction


class UnsupportedFileTypeError(Exception):
    def __init__(self, content_type: str) -> None:
        super().__init__(f"Unsupported file type: {content_type}")
        self.content_type = content_type


def extract_text(content_type: str, data: bytes) -> str:
    if content_type == PDF_CONTENT_TYPE:
        return _extract_pdf(data)
    if content_type == DOCX_CONTENT_TYPE:
        return _extract_docx(data)
    raise UnsupportedFileTypeError(content_type)


def _extract_pdf(data: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


async def parse_resume(
    gateway: LLMGateway, *, model: str, text: str
) -> tuple[ProfileData, dict[str, float]]:
    prompt = load_prompt("resume_extraction").format(resume_text=text)
    extraction = await gateway.complete_structured(
        [LLMMessage(role="user", content=prompt)],
        model=model,
        schema=ResumeExtraction,
    )
    profile = ProfileData.model_validate(extraction.model_dump(exclude={"confidence"}))
    return profile, extraction.confidence
