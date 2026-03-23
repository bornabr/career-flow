from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import get_settings
from app.api import parse, generate, pdf, cover_letter, chat
from app.services.pdf import shutdown_browser
from app.services.session_store import SessionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    db_path = Path(settings.langgraph_sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    checkpointer = AsyncSqliteSaver.from_conn_string(str(db_path))
    await checkpointer.setup()

    session_store = SessionStore(str(db_path))

    app.state.checkpointer = checkpointer
    app.state.session_store = session_store

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
