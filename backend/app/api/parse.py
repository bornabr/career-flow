"""Parse API routes - document upload and text extraction."""

import logging
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import get_settings
from app.services.parser import parse_document as parse_doc, SUPPORTED_CONTENT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/parse")
async def parse_documents(
    files: Annotated[list[UploadFile], File(description="One or more documents to parse")],
):
    """Parse uploaded documents (PDF, DOCX, image, txt) and extract text.

    Accepts multiple files. Each file is parsed independently and the results
    are returned as a list. The combined text (with source labels) is also
    provided for direct use in CV generation.

    Returns:
        {
            "files": [{"text": "...", "filename": "...", "content_type": "..."}],
            "combined_text": "--- Source: file1.pdf ---\\n...\\n--- Source: file2.docx ---\\n..."
        }
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    parsed_files: list[dict[str, str]] = []

    for file in files:
        content_type = file.content_type or "application/octet-stream"
        if content_type not in SUPPORTED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type for '{file.filename}': {content_type}. "
                f"Supported: {', '.join(SUPPORTED_CONTENT_TYPES.keys())}",
            )

        file_bytes = await file.read()
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File '{file.filename}' too large. Max size: {settings.max_upload_size_mb}MB",
            )

        try:
            text = parse_doc(file_bytes, content_type, file.filename or "document")
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Error parsing '{file.filename}': {e}")
        except Exception:
            logger.exception("Document parsing failed for %s", file.filename)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse '{file.filename}'",
            )

        parsed_files.append({
            "text": text,
            "filename": file.filename or "document",
            "content_type": content_type,
        })

    # Build combined text with source labels for multi-document context
    if len(parsed_files) == 1:
        combined_text = parsed_files[0]["text"]
    else:
        sections = []
        for pf in parsed_files:
            sections.append(f"--- Source: {pf['filename']} ---\n{pf['text']}")
        combined_text = "\n\n".join(sections)

    return {
        "files": parsed_files,
        "combined_text": combined_text,
    }
