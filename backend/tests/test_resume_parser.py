import io

import pytest
from docx import Document
from reportlab.pdfgen import canvas

from app.core.media_types import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from app.services.resume_parser import UnsupportedFileTypeError, extract_text


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pdf_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_extract_docx() -> None:
    text = extract_text(DOCX_CONTENT_TYPE, _docx_bytes("Jane Doe - Data Engineer"))
    assert "Jane Doe" in text
    assert "Data Engineer" in text


def test_extract_pdf() -> None:
    text = extract_text(PDF_CONTENT_TYPE, _pdf_bytes("Jane Doe - Data Engineer"))
    assert "Jane Doe" in text


def test_unsupported_type_raises() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        extract_text("text/plain", b"hello")
