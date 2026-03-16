"""Document parsing service — extract text from uploaded files.

Supports PDF (PyMuPDF fast path + Docling OCR fallback), DOCX, images, and plain text.
Includes post-extraction text normalization and source labeling for multi-document pipelines.
"""

import logging
import re
from io import BytesIO

import fitz
import pymupdf4llm
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)

_converter: DocumentConverter | None = None

SUPPORTED_CONTENT_TYPES = {
    "application/pdf": InputFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": InputFormat.DOCX,
    "image/png": InputFormat.IMAGE,
    "image/jpeg": InputFormat.IMAGE,
    "image/webp": InputFormat.IMAGE,
    "image/tiff": InputFormat.IMAGE,
    "text/plain": None,
}

# Minimum characters for a valid extraction (avoids near-empty results)
_MIN_TEXT_LENGTH = 50


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True

        _converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.IMAGE],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            },
        )
    return _converter


def _normalize_text(text: str) -> str:
    """Clean up extracted text for downstream LLM consumption.

    - Collapse 3+ consecutive newlines into 2
    - Strip trailing whitespace per line
    - Remove null bytes and control characters (except newline/tab)
    - Normalize unicode whitespace to ASCII space
    """
    # Remove null bytes and non-printable control chars (keep \n, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize unicode whitespace (non-breaking space, etc.) to regular space
    text = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", text)

    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _parse_with_pymupdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF + pymupdf4llm (fast, text-layer PDFs)."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        text = pymupdf4llm.to_markdown(doc)
    finally:
        doc.close()
    if not text or len(text.strip()) < _MIN_TEXT_LENGTH:
        raise ValueError("PyMuPDF extracted insufficient text — likely scanned PDF")
    return text


def _parse_with_docling(file_bytes: bytes, filename: str) -> str:
    """Extract text using Docling (OCR-capable, handles scanned docs and images)."""
    converter = _get_converter()
    stream = DocumentStream(name=filename, stream=BytesIO(file_bytes))
    result = converter.convert(stream)
    text = result.document.export_to_markdown()
    if not text or len(text.strip()) < _MIN_TEXT_LENGTH:
        raise ValueError(
            f"Docling extracted insufficient text from '{filename}'. "
            "The file may be empty, corrupted, or contain only images without recognizable text."
        )
    return text


def parse_document(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Extract text from an uploaded document.

    Strategy:
    - Plain text: decode directly
    - PDF: try PyMuPDF (fast) first, fall back to Docling (OCR-capable)
    - DOCX/Images: use Docling directly

    Returns normalized text with a source label header for multi-document pipelines.

    Raises:
        ValueError: If the file type is unsupported or extraction yields insufficient text.
    """
    if content_type not in SUPPORTED_CONTENT_TYPES:
        supported_list = ", ".join(SUPPORTED_CONTENT_TYPES.keys())
        raise ValueError(
            f"Unsupported file type: {content_type}. Supported: {supported_list}"
        )

    if content_type == "text/plain":
        try:
            raw_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = file_bytes.decode("utf-8", errors="replace")
            logger.warning("Non-UTF-8 characters in '%s' replaced during decoding", filename)
    elif content_type == "application/pdf":
        try:
            raw_text = _parse_with_pymupdf(file_bytes)
        except Exception as exc:
            logger.info("PyMuPDF failed for '%s' (%s), falling back to Docling", filename, exc)
            raw_text = _parse_with_docling(file_bytes, filename)
    else:
        raw_text = _parse_with_docling(file_bytes, filename)

    normalized = _normalize_text(raw_text)

    if len(normalized) < _MIN_TEXT_LENGTH:
        raise ValueError(
            f"Extracted text from '{filename}' is too short ({len(normalized)} chars). "
            "The file may be empty or contain only non-text content."
        )

    return normalized


def parse_documents(
    files: list[tuple[bytes, str, str]],
) -> str:
    """Parse multiple documents and combine with source labels.

    Args:
        files: List of (file_bytes, content_type, filename) tuples.

    Returns:
        Combined text with source labels separating each document:
        ``--- Source: resume.pdf ---``
        ``[extracted text]``
        ``--- Source: portfolio.pdf ---``
        ``[extracted text]``
    """
    parts: list[str] = []
    for file_bytes, content_type, filename in files:
        text = parse_document(file_bytes, content_type, filename)
        parts.append(f"--- Source: {filename} ---\n{text}")
    return "\n\n".join(parts)
