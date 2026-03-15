import logging
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


def _parse_with_pymupdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = pymupdf4llm.to_markdown(doc)
    doc.close()
    if not text or len(text.strip()) < 50:
        raise ValueError("PyMuPDF extracted insufficient text — likely scanned PDF")
    return text


def _parse_with_docling(file_bytes: bytes, filename: str) -> str:
    converter = _get_converter()
    stream = DocumentStream(name=filename, stream=BytesIO(file_bytes))
    result = converter.convert(stream)
    return result.document.export_to_markdown()


def parse_document(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Extract text from an uploaded document.

    Strategy:
    - Plain text: decode directly
    - PDF: try PyMuPDF (fast) first, fall back to Docling (OCR-capable)
    - DOCX/Images: use Docling directly
    """
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError(
            f"Unsupported file type: {content_type}. "
            f"Supported: {', '.join(SUPPORTED_CONTENT_TYPES.keys())}"
        )

    if content_type == "text/plain":
        return file_bytes.decode("utf-8")

    if content_type == "application/pdf":
        try:
            return _parse_with_pymupdf(file_bytes)
        except Exception as e:
            logger.info("PyMuPDF fallback failed (%s), using Docling", e)
            return _parse_with_docling(file_bytes, filename)

    return _parse_with_docling(file_bytes, filename)
