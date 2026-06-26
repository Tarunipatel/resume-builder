import io
import re
import pdfplumber
from docx import Document
from models import ParsedCV


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_email(text: str) -> str:
    match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else "Not found"


def extract_phone(text: str) -> str:
    match = re.search(r"(\+91[\s-]?)?[6-9]\d{9}|(\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
    return match.group(0) if match else "Not found"


def parse_cv(filename: str, file_bytes: bytes) -> ParsedCV:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_bytes)
    elif lower.endswith(".docx"):
        raw_text = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}. Only PDF and DOCX are supported.")

    if not raw_text.strip():
        raise ValueError(f"Could not extract text from {filename}. The file may be image-based or corrupted.")

    return ParsedCV(
        filename=filename,
        raw_text=raw_text,
        email=extract_email(raw_text),
        phone=extract_phone(raw_text),
    )
