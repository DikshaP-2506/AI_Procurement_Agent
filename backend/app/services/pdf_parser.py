import fitz
from typing import Optional


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF (fitz)."""
    try:
        doc = fitz.open(stream=file_bytes, filetype='pdf')
        pages = []
        for page in doc:
            pages.append(page.get_text())
        return "\n".join(pages)
    except Exception:
        return ""
