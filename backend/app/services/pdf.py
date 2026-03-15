"""PDF generation service — Jinja2 templates + Playwright page.pdf()."""

import logging
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from markupsafe import Markup
from playwright.async_api import async_playwright, Playwright, Browser

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

AVAILABLE_TEMPLATES = ["engineering", "classic", "modern"]

_playwright: Playwright | None = None
_browser: Browser | None = None

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


async def _get_browser() -> Browser:
    """Lazy-init singleton Chromium browser."""
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
    return _browser


async def shutdown_browser() -> None:
    """Close the singleton browser. Call on app shutdown."""
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


def render_html(cv_data: dict, template_name: str = "engineering", custom_styles: dict | None = None) -> str:
    """Render CV data to an HTML string using a Jinja2 template.

    Args:
        cv_data: CV dict matching the CV Pydantic model schema.
        template_name: One of 'engineering', 'classic', 'modern'.
        custom_styles: Optional overrides: primary_color, font_family, font_size, margin.

    Returns:
        Complete HTML string ready for Playwright rendering.
    """
    template_file = f"{template_name}.html"
    try:
        template = _jinja_env.get_template(template_file)
    except TemplateNotFound:
        raise ValueError(
            f"Template '{template_name}' not found. Available: {', '.join(AVAILABLE_TEMPLATES)}"
        )

    return template.render(cv=cv_data, custom_styles=custom_styles or {})


async def generate_pdf(
    cv_data: dict,
    template_name: str = "engineering",
    custom_styles: dict | None = None,
) -> bytes:
    """Render CV data to PDF via Playwright.

    1. Render Jinja2 HTML template with CV data
    2. Load into headless Chromium
    3. Generate PDF (US Letter, print backgrounds enabled)

    Args:
        cv_data: CV dict matching the CV Pydantic model schema.
        template_name: Template to use ('engineering', 'classic', 'modern').
        custom_styles: Optional style overrides.

    Returns:
        PDF file as bytes.
    """
    html = render_html(cv_data, template_name, custom_styles)

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
