"""PDF generation service — Jinja2 templates + Playwright page.pdf().

Renders CV data to HTML via Jinja2 templates, then converts to PDF using headless
Chromium. Includes retry logic for browser failures and input validation.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from markupsafe import Markup
from playwright.async_api import async_playwright, Playwright, Browser, Error as PlaywrightError

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

AVAILABLE_TEMPLATES = ["engineering", "classic", "modern"]

# Browser singleton
_playwright: Playwright | None = None
_browser: Browser | None = None

# PDF generation timeout (seconds)
_PDF_TIMEOUT = 30

# Max retries for browser operations
_MAX_RETRIES = 2

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _md_inline(text: str) -> Markup:
    """Convert **bold** and *italic* markdown to HTML <strong>/<em> tags."""
    escaped = Markup.escape(text)
    result = _BOLD_RE.sub(r"<strong>\1</strong>", str(escaped))
    result = _ITALIC_RE.sub(r"<em>\1</em>", result)
    return Markup(result)


_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False,
)
_jinja_env.filters["md"] = _md_inline


def _validate_cv_data(cv_data: dict[str, Any]) -> None:
    """Validate that cv_data has the minimum required fields for template rendering.

    Raises ValueError with a descriptive message if validation fails.
    """
    if not isinstance(cv_data, dict):
        raise ValueError("cv_data must be a dictionary")

    if not cv_data.get("name"):
        raise ValueError("cv_data.name is required for PDF generation")

    sections = cv_data.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("cv_data.sections must be a dictionary")

    # At minimum, Summary and Experience should exist
    if "Summary" not in sections:
        raise ValueError("cv_data.sections.Summary is required")
    if "Experience" not in sections:
        raise ValueError("cv_data.sections.Experience is required")


async def _get_browser() -> Browser:
    """Lazy-init singleton Chromium browser with reconnection support."""
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        if _playwright is not None:
            try:
                await _playwright.stop()
            except Exception:
                pass
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        logger.info("Chromium browser launched for PDF generation")
    return _browser


async def _reset_browser() -> None:
    """Force-reset the browser singleton (used after failures)."""
    global _playwright, _browser
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            pass
        _playwright = None
    logger.info("Browser singleton reset")


async def shutdown_browser() -> None:
    """Close the singleton browser. Call on app shutdown."""
    await _reset_browser()


def render_html(
    cv_data: dict[str, Any],
    template_name: str = "engineering",
    custom_styles: dict[str, Any] | None = None,
) -> str:
    """Render CV data to an HTML string using a Jinja2 template.

    Args:
        cv_data: CV dict matching the CV Pydantic model schema.
        template_name: One of 'engineering', 'classic', 'modern'.
        custom_styles: Optional overrides: primary_color, font_family, font_size, margin.

    Returns:
        Complete HTML string ready for Playwright rendering.

    Raises:
        ValueError: If template_name is not available or cv_data is invalid.
    """
    _validate_cv_data(cv_data)

    template_file = f"{template_name}.html"
    try:
        template = _jinja_env.get_template(template_file)
    except TemplateNotFound:
        raise ValueError(
            f"Template '{template_name}' not found. Available: {', '.join(AVAILABLE_TEMPLATES)}"
        )

    return template.render(cv=cv_data, custom_styles=custom_styles or {})


async def generate_pdf(
    cv_data: dict[str, Any],
    template_name: str = "engineering",
    custom_styles: dict[str, Any] | None = None,
) -> bytes:
    """Render CV data to PDF via Playwright.

    1. Validate cv_data has required fields
    2. Render Jinja2 HTML template with CV data
    3. Load into headless Chromium
    4. Generate PDF (US Letter, print backgrounds enabled)

    Includes retry logic: if the browser fails (crash, disconnect), it resets
    the singleton and retries once before raising.

    Args:
        cv_data: CV dict matching the CV Pydantic model schema.
        template_name: Template to use ('engineering', 'classic', 'modern').
        custom_styles: Optional style overrides.

    Returns:
        PDF file as bytes.

    Raises:
        ValueError: If cv_data is invalid or template not found.
        RuntimeError: If PDF generation fails after retries.
    """
    html = render_html(cv_data, template_name, custom_styles)

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await asyncio.wait_for(
                _render_pdf_from_html(html),
                timeout=_PDF_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error(
                "PDF generation timed out (attempt %d/%d, timeout=%ds)",
                attempt + 1,
                _MAX_RETRIES,
                _PDF_TIMEOUT,
            )
            last_error = TimeoutError(f"PDF generation timed out after {_PDF_TIMEOUT}s")
            await _reset_browser()
        except PlaywrightError as exc:
            logger.error(
                "Playwright error during PDF generation (attempt %d/%d): %s",
                attempt + 1,
                _MAX_RETRIES,
                exc,
            )
            last_error = exc
            await _reset_browser()

    raise RuntimeError(
        f"PDF generation failed after {_MAX_RETRIES} attempts: {last_error}"
    )


async def _render_pdf_from_html(html: str) -> bytes:
    """Internal: render HTML to PDF bytes using Playwright."""
    browser = await _get_browser()
    context = await browser.new_context()
    page = await context.new_page()

    try:
        await page.set_content(html, wait_until="networkidle")
        await page.emulate_media(media="print")

        pdf_bytes = await page.pdf(
            format="Letter",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
    finally:
        await context.close()

    return pdf_bytes
