from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import parse, generate, pdf, cover_letter, chat
from app.services.pdf import shutdown_browser


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — cleanup Playwright browser on shutdown."""
    yield
    await shutdown_browser()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(parse.router, prefix="/api", tags=["parse"])
    app.include_router(generate.router, prefix="/api", tags=["generate"])
    app.include_router(pdf.router, prefix="/api", tags=["pdf"])
    app.include_router(cover_letter.router, prefix="/api", tags=["cover-letter"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
