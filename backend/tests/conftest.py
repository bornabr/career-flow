"""Pytest configuration and shared fixtures."""
import pytest
from contextlib import asynccontextmanager
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver


@asynccontextmanager
async def _test_lifespan(app):
    """Test lifespan that uses MemorySaver instead of AsyncSqliteSaver."""
    app.state.checkpointer = MemorySaver()
    app.state.session_store = MagicMock()
    yield


@pytest.fixture
def client():
    """FastAPI test client fixture with in-memory checkpointer."""
    from app.main import create_app

    app = create_app()
    app.router.lifespan_context = _test_lifespan
    with TestClient(app) as c:
        yield c
