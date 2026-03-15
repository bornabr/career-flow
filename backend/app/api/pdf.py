"""PDF API routes - CV to PDF rendering via Playwright."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.pdf import generate_pdf, render_html, AVAILABLE_TEMPLATES

logger = logging.getLogger(__name__)

router = APIRouter()


class PDFRequest(BaseModel):
    """Request body for PDF generation."""

    cv_data: dict
    template: str = "engineering"
    custom_styles: dict | None = None


class PreviewRequest(BaseModel):
    """Request body for HTML preview."""

    cv_data: dict
    template: str = "engineering"
    custom_styles: dict | None = None


@router.get("/templates")
async def list_templates():
    """List available CV templates."""
    return {"templates": AVAILABLE_TEMPLATES}


@router.post("/pdf")
async def create_pdf(request: PDFRequest):
    """Render CV data to PDF using Playwright (HTML/CSS → page.pdf()).

    Supports multiple templates and custom styling (colors, fonts, margins).
    Returns the PDF as a downloadable file.
    """
    if request.template not in AVAILABLE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template: '{request.template}'. Available: {', '.join(AVAILABLE_TEMPLATES)}",
        )

    try:
        pdf_bytes = await generate_pdf(
            cv_data=request.cv_data,
            template_name=request.template,
            custom_styles=request.custom_styles,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"},
    )


@router.post("/preview")
async def preview_html(request: PreviewRequest):
    """Render CV data to HTML for live preview (no PDF conversion).

    Returns raw HTML that can be displayed in an iframe on the frontend.
    """
    if request.template not in AVAILABLE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template: '{request.template}'. Available: {', '.join(AVAILABLE_TEMPLATES)}",
        )

    try:
        html = render_html(
            cv_data=request.cv_data,
            template_name=request.template,
            custom_styles=request.custom_styles,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(content=html, media_type="text/html")
